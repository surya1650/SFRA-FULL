"""Result dataclasses for the analysis engine.

Two modes share one envelope (``AnalysisOutcome``) so downstream renderers
(DB writers, report builders, frontend) only need one decoder:

    AnalysisOutcome
      ├── mode = "comparative"      → result: ComparativeResult
      └── mode = "reference_missing_analysis" → result: StandaloneResult

Severity values are the spec v2 §3 enum names. Mode 2 does not assign a
spec-grade severity (no reference to compare against); it uses the special
``Severity.INDETERMINATE`` and emits self-analysis remarks instead.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import numpy as np


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class AnalysisMode(str, Enum):
    """Whether a reference trace was available at the time of analysis."""

    COMPARATIVE = "comparative"
    REFERENCE_MISSING = "reference_missing_analysis"


class Severity(str, Enum):
    """Per spec v2 §3 + Mode 2 extension.

    Mode 1 (comparative) emits NORMAL / MINOR_DEVIATION /
    SIGNIFICANT_DEVIATION / SEVERE_DEVIATION. Mode 2 (standalone)
    emits APPEARS_NORMAL / SUSPECT / INDETERMINATE — these are
    qualitative because no reference baseline is available.
    """

    # Mode 1 (comparative) — spec v2 §3 enum
    NORMAL = "NORMAL"
    MINOR_DEVIATION = "MINOR_DEVIATION"
    SIGNIFICANT_DEVIATION = "SIGNIFICANT_DEVIATION"
    SEVERE_DEVIATION = "SEVERE_DEVIATION"

    # Mode 2 (standalone) — qualitative
    APPEARS_NORMAL = "APPEARS_NORMAL"
    SUSPECT = "SUSPECT"
    INDETERMINATE = "INDETERMINATE"


# ---------------------------------------------------------------------------
# Trace container
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class TraceData:
    """Normalised SFRA trace (post-parse)."""

    frequency_hz: np.ndarray
    magnitude_db: np.ndarray
    phase_deg: Optional[np.ndarray] = None
    label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.frequency_hz = np.asarray(self.frequency_hz, dtype=float)
        self.magnitude_db = np.asarray(self.magnitude_db, dtype=float)
        if self.phase_deg is not None:
            self.phase_deg = np.asarray(self.phase_deg, dtype=float)
        if self.frequency_hz.shape != self.magnitude_db.shape:
            raise ValueError(
                f"frequency/magnitude length mismatch: "
                f"{self.frequency_hz.shape} vs {self.magnitude_db.shape}"
            )

    @property
    def n_points(self) -> int:
        return int(self.frequency_hz.size)

    @property
    def freq_min(self) -> float:
        return float(self.frequency_hz.min())

    @property
    def freq_max(self) -> float:
        return float(self.frequency_hz.max())


# ---------------------------------------------------------------------------
# Per-band statistical indices (Mode 1)
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class BandIndices:
    """Statistical indices for one band (per spec v2 §7.3)."""

    band_code: str  # LOW / MID_L / MID / HIGH / FULL
    f_low: Optional[float]
    f_high: Optional[float]
    n_points: int

    cc: Optional[float] = None        # uncentered cosine sim per spec v2
    asle: Optional[float] = None      # mean(|X-Y|), inputs in dB
    csd: Optional[float] = None       # sqrt(sum((X-Y)^2)/(N-1))
    min_max_ratio: Optional[float] = None
    max_dev_db: Optional[float] = None
    max_dev_freq_hz: Optional[float] = None
    rl_factor: Optional[float] = None  # DL/T 911 RLx = -log10(1 - CC)


# ---------------------------------------------------------------------------
# Mode 1 — comparative
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class ResonancePair:
    """One reference resonance matched (or not) to a tested resonance."""

    kind: str  # 'resonance' | 'anti_resonance'
    ref_frequency_hz: Optional[float]
    test_frequency_hz: Optional[float]
    shift_pct: Optional[float]
    delta_db: Optional[float]
    classification: str  # 'matched' | 'lost' | 'new'


@dataclass(slots=True)
class ComparativeResult:
    """Full Mode 1 comparison output."""

    band_indices: list[BandIndices]
    full_band_indices: BandIndices
    resonances_ref: list[dict[str, Any]]
    resonances_test: list[dict[str, Any]]
    resonance_pairs: list[ResonancePair]
    n_matched: int
    n_lost: int
    n_new: int
    poles_ref: list[dict[str, Any]] = field(default_factory=list)
    poles_test: list[dict[str, Any]] = field(default_factory=list)
    band_severity: dict[str, Severity] = field(default_factory=dict)
    overall_severity: Severity = Severity.INDETERMINATE
    auto_remarks: str = ""


# ---------------------------------------------------------------------------
# Mode 2 — standalone (reference missing)
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class BandEnergy:
    """Energy / dispersion summary for one band on a single trace."""

    band_code: str
    f_low: Optional[float]
    f_high: Optional[float]
    n_points: int
    rms_db: Optional[float] = None
    mean_db: Optional[float] = None
    std_db: Optional[float] = None
    range_db: Optional[float] = None  # max - min within band
    n_resonances: int = 0
    n_antiresonances: int = 0


@dataclass(slots=True)
class StandaloneResult:
    """Mode 2 output — analysis without a reference baseline.

    Per the user's directive: detect resonances, band behaviour, anomalies;
    emit qualitative remarks; flag suspicious patterns. When a reference
    becomes available later, the runner will replay this trace through
    Mode 1 and supersede the standalone result.
    """

    band_energy: list[BandEnergy]
    full_band_energy: BandEnergy
    resonances: list[dict[str, Any]]
    n_resonances: int
    n_antiresonances: int
    resonance_density_per_decade: float
    peak_irregularity_score: float    # 0.0 = regular, 1.0 = highly irregular
    noise_floor_db: Optional[float]
    snr_estimate_db: Optional[float]
    abnormal_damping_flags: list[str]
    anomaly_flags: list[str]
    qualitative_severity: Severity   # APPEARS_NORMAL / SUSPECT / INDETERMINATE
    auto_remarks: str
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Unified envelope
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class AnalysisOutcome:
    """One envelope for both modes — discriminated by ``mode``.

    Exactly one of ``comparative`` / ``standalone`` is populated.
    """

    mode: AnalysisMode
    transformer_type: Optional[str] = None
    combination_code: Optional[str] = None
    tested_label: str = ""
    reference_label: Optional[str] = None
    generated_at: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    engine_version: str = "0.1.0-phase0"

    comparative: Optional[ComparativeResult] = None
    standalone: Optional[StandaloneResult] = None

    @property
    def severity(self) -> Severity:
        if self.mode == AnalysisMode.COMPARATIVE and self.comparative is not None:
            return self.comparative.overall_severity
        if self.mode == AnalysisMode.REFERENCE_MISSING and self.standalone is not None:
            return self.standalone.qualitative_severity
        return Severity.INDETERMINATE

    @property
    def auto_remarks(self) -> str:
        if self.mode == AnalysisMode.COMPARATIVE and self.comparative is not None:
            return self.comparative.auto_remarks
        if self.mode == AnalysisMode.REFERENCE_MISSING and self.standalone is not None:
            return self.standalone.auto_remarks
        return ""

    def to_dict(self) -> dict[str, Any]:
        """JSON-friendly dump (numpy arrays → lists, datetimes → isoformat)."""
        d = asdict(self)
        d["mode"] = self.mode.value
        d["generated_at"] = self.generated_at.isoformat()
        d["severity"] = self.severity.value
        return _strip_numpy(d)


def _strip_numpy(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _strip_numpy(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_strip_numpy(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj
