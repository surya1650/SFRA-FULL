"""DB enums — kept as a separate module so Alembic migrations can import
them without pulling in the analysis stack.

Severity / AnalysisMode duplicate the names defined in
``sfra_analysis.result_types`` because the DB enum needs to be a stable
SQL-side string set decoupled from Python imports. Conversion helpers
live below.
"""
from __future__ import annotations

import enum

from sfra_full.sfra_analysis.result_types import AnalysisMode, Severity


class TransformerType(str, enum.Enum):
    """Spec v2 §3 ``transformer_type`` ENUM."""

    TWO_WINDING = "TWO_WINDING"
    AUTO_WITH_TERTIARY_BROUGHT_OUT = "AUTO_WITH_TERTIARY_BROUGHT_OUT"
    AUTO_WITH_TERTIARY_BURIED = "AUTO_WITH_TERTIARY_BURIED"
    THREE_WINDING = "THREE_WINDING"


class InterventionType(str, enum.Enum):
    """OverhaulCycle.intervention_type — spec v2 §3."""

    COMMISSIONING = "COMMISSIONING"
    MAJOR_OVERHAUL = "MAJOR_OVERHAUL"
    ACTIVE_PART_INSPECTION = "ACTIVE_PART_INSPECTION"
    WINDING_REPLACEMENT = "WINDING_REPLACEMENT"
    RELOCATION = "RELOCATION"
    OTHER = "OTHER"


class SessionType(str, enum.Enum):
    """TestSession.session_type — spec v2 §3."""

    REFERENCE = "REFERENCE"
    ROUTINE = "ROUTINE"
    POST_FAULT = "POST_FAULT"
    POST_OVERHAUL = "POST_OVERHAUL"
    COMMISSIONING = "COMMISSIONING"


class TraceRole(str, enum.Enum):
    """Trace.role — REFERENCE traces live in the active OverhaulCycle and
    are immutable once the cycle closes; TESTED traces are everything else.
    """

    REFERENCE = "REFERENCE"
    TESTED = "TESTED"


class SourceFormat(str, enum.Enum):
    """Trace.source_file_format."""

    FRAX = "FRAX"
    FRAX_LEGACY = "FRAX_LEGACY"
    CSV = "CSV"
    XFRA = "XFRA"
    XML = "XML"
    FRA = "FRA"
    SFRA = "SFRA"


class AnalysisModeDB(str, enum.Enum):
    """Mirror of ``AnalysisMode`` for DB-side storage."""

    COMPARATIVE = AnalysisMode.COMPARATIVE.value
    REFERENCE_MISSING_ANALYSIS = AnalysisMode.REFERENCE_MISSING.value


class SeverityDB(str, enum.Enum):
    """Mirror of ``Severity`` for DB-side storage. Spans Mode 1 + Mode 2."""

    NORMAL = Severity.NORMAL.value
    MINOR_DEVIATION = Severity.MINOR_DEVIATION.value
    SIGNIFICANT_DEVIATION = Severity.SIGNIFICANT_DEVIATION.value
    SEVERE_DEVIATION = Severity.SEVERE_DEVIATION.value
    APPEARS_NORMAL = Severity.APPEARS_NORMAL.value
    SUSPECT = Severity.SUSPECT.value
    INDETERMINATE = Severity.INDETERMINATE.value


def severity_to_db(s: Severity) -> SeverityDB:
    return SeverityDB(s.value)


def severity_from_db(s: SeverityDB | str) -> Severity:
    return Severity(s.value if isinstance(s, SeverityDB) else s)


def mode_to_db(m: AnalysisMode) -> AnalysisModeDB:
    return AnalysisModeDB(m.value)


def mode_from_db(m: AnalysisModeDB | str) -> AnalysisMode:
    return AnalysisMode(m.value if isinstance(m, AnalysisModeDB) else m)


__all__ = [
    "AnalysisModeDB",
    "InterventionType",
    "SessionType",
    "SeverityDB",
    "SourceFormat",
    "TraceRole",
    "TransformerType",
    "mode_from_db",
    "mode_to_db",
    "severity_from_db",
    "severity_to_db",
]
