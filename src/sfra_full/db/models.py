"""SQLAlchemy 2.x typed models — spec v2 §3 tables.

All six entities live here so a fresh `import sfra_full.db.models` registers
the full schema on the metadata. Alembic autogenerate consumes this module.

Notes:
- ``SQLEnum`` is the standard portable enum (stored as VARCHAR with a
  CHECK constraint on PostgreSQL, plain TEXT on SQLite).
- ``LargeBinary`` maps to BYTEA on PostgreSQL and BLOB on SQLite.
- ``JSON`` works on both — we don't use JSONB-specific operators yet.
- ``DateTime(timezone=True)`` — always store UTC; the API converts.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import (
    AnalysisModeDB,
    InterventionType,
    SessionType,
    SeverityDB,
    SourceFormat,
    TraceRole,
    TransformerType,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# Transformer
# ---------------------------------------------------------------------------
class Transformer(Base):
    __tablename__ = "transformer"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_uuid)
    serial_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    nameplate_mva: Mapped[Optional[float]] = mapped_column(Float)
    hv_kv: Mapped[Optional[float]] = mapped_column(Float)
    lv_kv: Mapped[Optional[float]] = mapped_column(Float)
    tv_kv: Mapped[Optional[float]] = mapped_column(Float)

    vector_group: Mapped[Optional[str]] = mapped_column(String(16))
    transformer_type: Mapped[TransformerType] = mapped_column(
        SQLEnum(TransformerType, name="transformer_type"), nullable=False
    )

    manufacturer: Mapped[Optional[str]] = mapped_column(String(80))
    year_of_manufacture: Mapped[Optional[int]] = mapped_column(Integer)
    substation: Mapped[Optional[str]] = mapped_column(String(120))
    feeder_bay: Mapped[Optional[str]] = mapped_column(String(64))

    has_oltc: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    oltc_make: Mapped[Optional[str]] = mapped_column(String(80))
    oltc_steps_total: Mapped[Optional[int]] = mapped_column(Integer)
    oltc_step_pct: Mapped[Optional[float]] = mapped_column(Float)

    has_detc: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    detc_steps_total: Mapped[Optional[int]] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    overhaul_cycles: Mapped[list["OverhaulCycle"]] = relationship(
        back_populates="transformer", cascade="all, delete-orphan"
    )
    test_sessions: Mapped[list["TestSession"]] = relationship(
        back_populates="transformer", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# OverhaulCycle
# ---------------------------------------------------------------------------
class OverhaulCycle(Base):
    """Spec v2 §3: open cycle (cycle_end_date IS NULL) holds the live references.

    A new cycle is opened on COMMISSIONING / MAJOR_OVERHAUL /
    ACTIVE_PART_INSPECTION; the prior cycle is closed and locked.
    """

    __tablename__ = "overhaul_cycle"
    __table_args__ = (
        UniqueConstraint("transformer_id", "cycle_no", name="uq_overhaul_cycle_no"),
        Index("ix_overhaul_cycle_open", "transformer_id", "cycle_end_date"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_uuid)
    transformer_id: Mapped[str] = mapped_column(
        ForeignKey("transformer.id", ondelete="CASCADE"), nullable=False
    )
    cycle_no: Mapped[int] = mapped_column(Integer, nullable=False)
    cycle_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    cycle_end_date: Mapped[Optional[date]] = mapped_column(Date)

    intervention_type: Mapped[InterventionType] = mapped_column(
        SQLEnum(InterventionType, name="intervention_type"), nullable=False
    )
    remarks: Mapped[Optional[str]] = mapped_column(Text)
    notes_pdf_path: Mapped[Optional[str]] = mapped_column(String(512))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    transformer: Mapped["Transformer"] = relationship(back_populates="overhaul_cycles")
    test_sessions: Mapped[list["TestSession"]] = relationship(
        back_populates="overhaul_cycle", cascade="all, delete-orphan"
    )

    @property
    def is_open(self) -> bool:
        return self.cycle_end_date is None


# ---------------------------------------------------------------------------
# TestSession
# ---------------------------------------------------------------------------
class TestSession(Base):
    # Pytest's auto-discovery treats classes starting with ``Test`` as test
    # cases by default; mark this ORM class as a non-test so pytest skips it.
    __test__ = False
    __tablename__ = "test_session"
    __table_args__ = (
        Index("ix_test_session_transformer_date", "transformer_id", "session_date"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_uuid)
    transformer_id: Mapped[str] = mapped_column(
        ForeignKey("transformer.id", ondelete="CASCADE"), nullable=False
    )
    overhaul_cycle_id: Mapped[str] = mapped_column(
        ForeignKey("overhaul_cycle.id", ondelete="CASCADE"), nullable=False
    )

    session_type: Mapped[SessionType] = mapped_column(
        SQLEnum(SessionType, name="session_type"), nullable=False
    )
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    tested_by: Mapped[Optional[str]] = mapped_column(String(120))
    witnessed_by: Mapped[Optional[str]] = mapped_column(String(120))

    ambient_temp_c: Mapped[Optional[float]] = mapped_column(Float)
    oil_temp_c: Mapped[Optional[float]] = mapped_column(Float)
    winding_temp_c: Mapped[Optional[float]] = mapped_column(Float)
    humidity_pct: Mapped[Optional[float]] = mapped_column(Float)

    instrument_make_model: Mapped[Optional[str]] = mapped_column(String(120))
    instrument_serial: Mapped[Optional[str]] = mapped_column(String(80))
    instrument_calibration_due_date: Mapped[Optional[date]] = mapped_column(Date)
    lead_length_m: Mapped[Optional[float]] = mapped_column(Float)
    remarks: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    transformer: Mapped["Transformer"] = relationship(back_populates="test_sessions")
    overhaul_cycle: Mapped["OverhaulCycle"] = relationship(back_populates="test_sessions")
    traces: Mapped[list["Trace"]] = relationship(
        back_populates="test_session", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Combination — seeded from standards/ieee_c57_149_combinations.yaml
# ---------------------------------------------------------------------------
class Combination(Base):
    __tablename__ = "combination"
    __table_args__ = (
        UniqueConstraint("transformer_type", "code", name="uq_combination_type_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transformer_type: Mapped[TransformerType] = mapped_column(
        SQLEnum(TransformerType, name="combination_transformer_type"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    winding: Mapped[str] = mapped_column(String(8), nullable=False)
    phase: Mapped[str] = mapped_column(String(2), nullable=False)
    injection_terminal: Mapped[str] = mapped_column(String(8), nullable=False)
    measurement_terminal: Mapped[str] = mapped_column(String(8), nullable=False)
    shorted_terminals: Mapped[Optional[list[str]]] = mapped_column(JSON)
    grounded_terminals: Mapped[Optional[list[str]]] = mapped_column(JSON)
    description: Mapped[Optional[str]] = mapped_column(Text)


# ---------------------------------------------------------------------------
# Trace
# ---------------------------------------------------------------------------
class Trace(Base):
    __tablename__ = "trace"
    __table_args__ = (
        Index("ix_trace_session_combination", "test_session_id", "combination_id"),
        Index("ix_trace_role", "role"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_uuid)
    test_session_id: Mapped[str] = mapped_column(
        ForeignKey("test_session.id", ondelete="CASCADE"), nullable=False
    )
    combination_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("combination.id", ondelete="SET NULL")
    )

    role: Mapped[TraceRole] = mapped_column(SQLEnum(TraceRole, name="trace_role"), nullable=False)
    label: Mapped[str] = mapped_column(String(160), default="", nullable=False)

    tap_position_current: Mapped[Optional[int]] = mapped_column(Integer)
    tap_position_previous: Mapped[Optional[int]] = mapped_column(Integer)
    tap_position_reference: Mapped[Optional[int]] = mapped_column(Integer)
    detc_tap_position: Mapped[Optional[int]] = mapped_column(Integer)

    source_file_path: Mapped[Optional[str]] = mapped_column(String(512))
    source_file_format: Mapped[SourceFormat] = mapped_column(
        SQLEnum(SourceFormat, name="source_file_format"), nullable=False
    )
    source_file_sha256: Mapped[Optional[str]] = mapped_column(String(64))
    sweep_index_in_source_file: Mapped[Optional[int]] = mapped_column(Integer)

    # BYTEA blobs for parsed numpy arrays (spec v2 §3).
    frequency_hz: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    magnitude_db: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    phase_deg: Mapped[Optional[bytes]] = mapped_column(LargeBinary)

    point_count: Mapped[int] = mapped_column(Integer, nullable=False)
    freq_min_hz: Mapped[float] = mapped_column(Float, nullable=False)
    freq_max_hz: Mapped[float] = mapped_column(Float, nullable=False)

    uploaded_by: Mapped[Optional[str]] = mapped_column(String(120))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)

    test_session: Mapped["TestSession"] = relationship(back_populates="traces")
    combination: Mapped[Optional["Combination"]] = relationship()
    analyses_as_tested: Mapped[list["AnalysisResult"]] = relationship(
        back_populates="tested_trace", foreign_keys="AnalysisResult.tested_trace_id"
    )


# ---------------------------------------------------------------------------
# AnalysisResult
# ---------------------------------------------------------------------------
class AnalysisResult(Base):
    __tablename__ = "analysis_result"
    __table_args__ = (
        Index(
            "ix_analysis_session_combo",
            "test_session_id",
            "combination_id",
        ),
        CheckConstraint(
            "(mode = 'reference_missing_analysis' AND reference_trace_id IS NULL) "
            "OR (mode = 'comparative' AND reference_trace_id IS NOT NULL)",
            name="mode_reference_consistency",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_uuid)
    test_session_id: Mapped[str] = mapped_column(
        ForeignKey("test_session.id", ondelete="CASCADE"), nullable=False
    )
    combination_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("combination.id", ondelete="SET NULL")
    )
    tested_trace_id: Mapped[str] = mapped_column(
        ForeignKey("trace.id", ondelete="CASCADE"), nullable=False
    )
    reference_trace_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("trace.id", ondelete="SET NULL")
    )

    # Spec v2 stores AnalysisMode / Severity by VALUE (e.g. 'comparative',
    # 'NORMAL') so the CHECK constraint can be expressed against the enum
    # values directly. Without ``values_callable`` SQLAlchemy stores the
    # Python enum NAME instead, which would diverge from the constraint.
    mode: Mapped[AnalysisModeDB] = mapped_column(
        SQLEnum(
            AnalysisModeDB,
            name="analysis_mode",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    severity: Mapped[SeverityDB] = mapped_column(
        SQLEnum(
            SeverityDB,
            name="severity",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )

    # Per-band & full-band metric snapshot. Stored as JSON for flexibility;
    # downstream UI / reports decode per the schema in result_types.py.
    indicators_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    resonances_json: Mapped[Optional[list[dict]]] = mapped_column(JSON)
    poles_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    standalone_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)

    auto_remarks: Mapped[Optional[str]] = mapped_column(Text)
    reviewer_remarks: Mapped[Optional[str]] = mapped_column(Text)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(120))
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    engine_version: Mapped[str] = mapped_column(String(32), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    tested_trace: Mapped["Trace"] = relationship(
        back_populates="analyses_as_tested", foreign_keys=[tested_trace_id]
    )
    reference_trace: Mapped[Optional["Trace"]] = relationship(
        foreign_keys=[reference_trace_id]
    )


__all__ = [
    "AnalysisResult",
    "Combination",
    "OverhaulCycle",
    "TestSession",
    "Trace",
    "Transformer",
]
