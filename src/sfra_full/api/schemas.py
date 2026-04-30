"""Pydantic v2 request / response DTOs for the FastAPI layer."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from sfra_full.db.enums import (
    AnalysisModeDB,
    InterventionType,
    SessionType,
    SeverityDB,
    SourceFormat,
    TraceRole,
    TransformerType,
)


# ---------------------------------------------------------------------------
# Transformer
# ---------------------------------------------------------------------------
class TransformerCreate(BaseModel):
    serial_no: str
    transformer_type: TransformerType
    nameplate_mva: Optional[float] = None
    hv_kv: Optional[float] = None
    lv_kv: Optional[float] = None
    tv_kv: Optional[float] = None
    vector_group: Optional[str] = None
    manufacturer: Optional[str] = None
    year_of_manufacture: Optional[int] = None
    substation: Optional[str] = None
    feeder_bay: Optional[str] = None
    has_oltc: bool = False
    oltc_make: Optional[str] = None
    oltc_steps_total: Optional[int] = None
    oltc_step_pct: Optional[float] = None
    has_detc: bool = False
    detc_steps_total: Optional[int] = None


class TransformerOut(TransformerCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# OverhaulCycle
# ---------------------------------------------------------------------------
class OverhaulCycleCreate(BaseModel):
    intervention_type: InterventionType
    cycle_start_date: date
    remarks: Optional[str] = None


class OverhaulCycleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    transformer_id: str
    cycle_no: int
    cycle_start_date: date
    cycle_end_date: Optional[date]
    intervention_type: InterventionType
    remarks: Optional[str]
    is_open: bool


# ---------------------------------------------------------------------------
# TestSession
# ---------------------------------------------------------------------------
class TestSessionCreate(BaseModel):
    overhaul_cycle_id: str
    session_type: SessionType
    session_date: date
    tested_by: Optional[str] = None
    witnessed_by: Optional[str] = None
    ambient_temp_c: Optional[float] = None
    oil_temp_c: Optional[float] = None
    winding_temp_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    instrument_make_model: Optional[str] = None
    instrument_serial: Optional[str] = None
    instrument_calibration_due_date: Optional[date] = None
    lead_length_m: Optional[float] = None
    remarks: Optional[str] = None


class TestSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    transformer_id: str
    overhaul_cycle_id: str
    session_type: SessionType
    session_date: date


# ---------------------------------------------------------------------------
# Combination
# ---------------------------------------------------------------------------
class CombinationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    transformer_type: TransformerType
    code: str
    sequence: int
    category: str
    winding: str
    phase: str
    injection_terminal: str
    measurement_terminal: str
    shorted_terminals: Optional[list[str]]
    grounded_terminals: Optional[list[str]]
    description: Optional[str]


# ---------------------------------------------------------------------------
# Trace
# ---------------------------------------------------------------------------
class TraceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    test_session_id: str
    combination_id: Optional[int] = None
    role: TraceRole
    label: str
    tap_position_current: Optional[int] = None
    source_file_format: SourceFormat
    source_file_sha256: Optional[str] = None
    point_count: int
    freq_min_hz: float
    freq_max_hz: float
    uploaded_at: datetime


class UploadResponse(BaseModel):
    """Response from POST /api/sessions/{id}/upload."""

    detected_format: str
    n_sweeps_parsed: int
    n_traces_persisted: int
    traces: list[TraceOut]
    unmapped_sweeps: list[dict[str, Any]] = Field(default_factory=list)


class UploadParams(BaseModel):
    """Multipart form parameters that accompany the file."""

    role: TraceRole = TraceRole.TESTED
    combination_code: Optional[str] = None  # if single-trace, override resolver
    tap_position_current: Optional[int] = None
    tap_position_previous: Optional[int] = None
    tap_position_reference: Optional[int] = None
    detc_tap_position: Optional[int] = None
    notes: Optional[str] = None
    uploaded_by: Optional[str] = None


# ---------------------------------------------------------------------------
# AnalysisResult
# ---------------------------------------------------------------------------
class AnalysisResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    test_session_id: str
    combination_id: Optional[int]
    tested_trace_id: str
    reference_trace_id: Optional[str]
    mode: AnalysisModeDB
    severity: SeverityDB
    indicators_json: Optional[dict[str, Any]] = None
    resonances_json: Optional[list[dict[str, Any]]] = None
    poles_json: Optional[dict[str, Any]] = None
    standalone_json: Optional[dict[str, Any]] = None
    auto_remarks: Optional[str] = None
    engine_version: str
    computed_at: datetime


class RunAnalysisResponse(BaseModel):
    n_results: int
    mode_1_count: int  # comparative
    mode_2_count: int  # reference_missing
    results: list[AnalysisResultOut]


__all__ = [
    "AnalysisResultOut",
    "CombinationOut",
    "OverhaulCycleCreate",
    "OverhaulCycleOut",
    "RunAnalysisResponse",
    "TestSessionCreate",
    "TestSessionOut",
    "TraceOut",
    "TransformerCreate",
    "TransformerOut",
    "UploadParams",
    "UploadResponse",
]
