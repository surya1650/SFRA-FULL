"""Initial schema — spec v2 §3 tables.

Revision ID: 20260426_0001
Revises:
Create Date: 2026-04-26
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260426_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Enum value lists kept here so this migration is self-contained.
TRANSFORMER_TYPES = (
    "TWO_WINDING",
    "AUTO_WITH_TERTIARY_BROUGHT_OUT",
    "AUTO_WITH_TERTIARY_BURIED",
    "THREE_WINDING",
)
INTERVENTION_TYPES = (
    "COMMISSIONING", "MAJOR_OVERHAUL", "ACTIVE_PART_INSPECTION",
    "WINDING_REPLACEMENT", "RELOCATION", "OTHER",
)
SESSION_TYPES = ("REFERENCE", "ROUTINE", "POST_FAULT", "POST_OVERHAUL", "COMMISSIONING")
TRACE_ROLES = ("REFERENCE", "TESTED")
SOURCE_FORMATS = ("FRAX", "FRAX_LEGACY", "CSV", "XFRA", "XML", "FRA", "SFRA")
ANALYSIS_MODES = ("comparative", "reference_missing_analysis")
SEVERITIES = (
    "NORMAL", "MINOR_DEVIATION", "SIGNIFICANT_DEVIATION", "SEVERE_DEVIATION",
    "APPEARS_NORMAL", "SUSPECT", "INDETERMINATE",
)


def upgrade() -> None:
    op.create_table(
        "transformer",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("serial_no", sa.String(64), nullable=False, unique=True),
        sa.Column("nameplate_mva", sa.Float()),
        sa.Column("hv_kv", sa.Float()),
        sa.Column("lv_kv", sa.Float()),
        sa.Column("tv_kv", sa.Float()),
        sa.Column("vector_group", sa.String(16)),
        sa.Column("transformer_type", sa.Enum(*TRANSFORMER_TYPES, name="transformer_type"), nullable=False),
        sa.Column("manufacturer", sa.String(80)),
        sa.Column("year_of_manufacture", sa.Integer()),
        sa.Column("substation", sa.String(120)),
        sa.Column("feeder_bay", sa.String(64)),
        sa.Column("has_oltc", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("oltc_make", sa.String(80)),
        sa.Column("oltc_steps_total", sa.Integer()),
        sa.Column("oltc_step_pct", sa.Float()),
        sa.Column("has_detc", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("detc_steps_total", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "overhaul_cycle",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("transformer_id", sa.String(32), sa.ForeignKey("transformer.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cycle_no", sa.Integer(), nullable=False),
        sa.Column("cycle_start_date", sa.Date(), nullable=False),
        sa.Column("cycle_end_date", sa.Date()),
        sa.Column("intervention_type", sa.Enum(*INTERVENTION_TYPES, name="intervention_type"), nullable=False),
        sa.Column("remarks", sa.Text()),
        sa.Column("notes_pdf_path", sa.String(512)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("transformer_id", "cycle_no", name="uq_overhaul_cycle_no"),
    )
    op.create_index("ix_overhaul_cycle_open", "overhaul_cycle", ["transformer_id", "cycle_end_date"])

    op.create_table(
        "test_session",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("transformer_id", sa.String(32), sa.ForeignKey("transformer.id", ondelete="CASCADE"), nullable=False),
        sa.Column("overhaul_cycle_id", sa.String(32), sa.ForeignKey("overhaul_cycle.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_type", sa.Enum(*SESSION_TYPES, name="session_type"), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("tested_by", sa.String(120)),
        sa.Column("witnessed_by", sa.String(120)),
        sa.Column("ambient_temp_c", sa.Float()),
        sa.Column("oil_temp_c", sa.Float()),
        sa.Column("winding_temp_c", sa.Float()),
        sa.Column("humidity_pct", sa.Float()),
        sa.Column("instrument_make_model", sa.String(120)),
        sa.Column("instrument_serial", sa.String(80)),
        sa.Column("instrument_calibration_due_date", sa.Date()),
        sa.Column("lead_length_m", sa.Float()),
        sa.Column("remarks", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_test_session_transformer_date", "test_session", ["transformer_id", "session_date"])

    op.create_table(
        "combination",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("transformer_type", sa.Enum(*TRANSFORMER_TYPES, name="combination_transformer_type"), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(16), nullable=False),
        sa.Column("winding", sa.String(8), nullable=False),
        sa.Column("phase", sa.String(2), nullable=False),
        sa.Column("injection_terminal", sa.String(8), nullable=False),
        sa.Column("measurement_terminal", sa.String(8), nullable=False),
        sa.Column("shorted_terminals", sa.JSON()),
        sa.Column("grounded_terminals", sa.JSON()),
        sa.Column("description", sa.Text()),
        sa.UniqueConstraint("transformer_type", "code", name="uq_combination_type_code"),
    )

    op.create_table(
        "trace",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("test_session_id", sa.String(32), sa.ForeignKey("test_session.id", ondelete="CASCADE"), nullable=False),
        sa.Column("combination_id", sa.Integer(), sa.ForeignKey("combination.id", ondelete="SET NULL")),
        sa.Column("role", sa.Enum(*TRACE_ROLES, name="trace_role"), nullable=False),
        sa.Column("label", sa.String(160), nullable=False, server_default=""),
        sa.Column("tap_position_current", sa.Integer()),
        sa.Column("tap_position_previous", sa.Integer()),
        sa.Column("tap_position_reference", sa.Integer()),
        sa.Column("detc_tap_position", sa.Integer()),
        sa.Column("source_file_path", sa.String(512)),
        sa.Column("source_file_format", sa.Enum(*SOURCE_FORMATS, name="source_file_format"), nullable=False),
        sa.Column("source_file_sha256", sa.String(64)),
        sa.Column("sweep_index_in_source_file", sa.Integer()),
        sa.Column("frequency_hz", sa.LargeBinary(), nullable=False),
        sa.Column("magnitude_db", sa.LargeBinary(), nullable=False),
        sa.Column("phase_deg", sa.LargeBinary()),
        sa.Column("point_count", sa.Integer(), nullable=False),
        sa.Column("freq_min_hz", sa.Float(), nullable=False),
        sa.Column("freq_max_hz", sa.Float(), nullable=False),
        sa.Column("uploaded_by", sa.String(120)),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text()),
    )
    op.create_index("ix_trace_session_combination", "trace", ["test_session_id", "combination_id"])
    op.create_index("ix_trace_role", "trace", ["role"])

    op.create_table(
        "analysis_result",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("test_session_id", sa.String(32), sa.ForeignKey("test_session.id", ondelete="CASCADE"), nullable=False),
        sa.Column("combination_id", sa.Integer(), sa.ForeignKey("combination.id", ondelete="SET NULL")),
        sa.Column("tested_trace_id", sa.String(32), sa.ForeignKey("trace.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reference_trace_id", sa.String(32), sa.ForeignKey("trace.id", ondelete="SET NULL")),
        sa.Column("mode", sa.Enum(*ANALYSIS_MODES, name="analysis_mode"), nullable=False),
        sa.Column("severity", sa.Enum(*SEVERITIES, name="severity"), nullable=False),
        sa.Column("indicators_json", sa.JSON()),
        sa.Column("resonances_json", sa.JSON()),
        sa.Column("poles_json", sa.JSON()),
        sa.Column("standalone_json", sa.JSON()),
        sa.Column("auto_remarks", sa.Text()),
        sa.Column("reviewer_remarks", sa.Text()),
        sa.Column("reviewed_by", sa.String(120)),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("engine_version", sa.String(32), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(mode = 'reference_missing_analysis' AND reference_trace_id IS NULL) "
            "OR (mode = 'comparative' AND reference_trace_id IS NOT NULL)",
            name="ck_analysis_result_mode_reference_consistency",
        ),
    )
    op.create_index(
        "ix_analysis_session_combo", "analysis_result", ["test_session_id", "combination_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_session_combo", table_name="analysis_result")
    op.drop_table("analysis_result")
    op.drop_index("ix_trace_role", table_name="trace")
    op.drop_index("ix_trace_session_combination", table_name="trace")
    op.drop_table("trace")
    op.drop_table("combination")
    op.drop_index("ix_test_session_transformer_date", table_name="test_session")
    op.drop_table("test_session")
    op.drop_index("ix_overhaul_cycle_open", table_name="overhaul_cycle")
    op.drop_table("overhaul_cycle")
    op.drop_table("transformer")
