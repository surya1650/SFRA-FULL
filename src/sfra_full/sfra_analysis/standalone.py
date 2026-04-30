"""Mode 2 — single-trace standalone analysis (no reference available).

Per the user directive:

    Mode 2: Single Trace Analysis
    1. Band energy distribution
    2. Resonance density
    3. Peak irregularity detection
    4. Noise / measurement validation
    5. Abnormal damping detection

    Generate qualitative remarks like:
        "Irregular resonance distribution in HF region"
        "Possible winding deformation indication (no reference available)"
        "Signature appears normal within statistical limits"

The output is returned as a ``StandaloneResult`` and wrapped in an
``AnalysisOutcome`` with mode=REFERENCE_MISSING. When a reference becomes
available later, the runner replays the trace through Mode 1 and the
standalone result is superseded.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np

from .bands import BANDS_SPEC_V2, BandSpec
from .result_types import (
    BandEnergy,
    Severity,
    StandaloneResult,
    TraceData,
)
from .transfer import detect_resonances


# Tunable thresholds — kept here so DECISIONS.md can record their rationale
# and engineering can adjust based on real APTRANSCO fixtures.
_HF_BAND = "HIGH"
_MID_BAND = "MID"
_NOISE_FLOOR_HF_HZ = 1_500_000.0   # use samples above this for noise estimation
_RESONANCE_DENSITY_HIGH = 8.0      # >8 peaks/decade → "very dense"
_RESONANCE_DENSITY_LOW = 0.5       # <0.5 peaks/decade → "sparse / suspicious"
_PEAK_IRREGULARITY_SUSPECT = 0.55  # cv of inter-peak log-spacing
_MIN_BAND_POINTS = 8


def _band_energy(
    frequency_hz: np.ndarray,
    magnitude_db: np.ndarray,
    band: Optional[BandSpec],
    resonances_in_band: list[dict],
) -> BandEnergy:
    if band is None:
        f = frequency_hz
        m = magnitude_db
        code = "FULL"
        f_lo: Optional[float] = float(f.min()) if f.size else None
        f_hi: Optional[float] = float(f.max()) if f.size else None
    else:
        f, m = band.slice(frequency_hz, magnitude_db)
        code = band.code
        f_lo = band.min_hz
        f_hi = band.max_hz

    n = int(f.size)
    if n < _MIN_BAND_POINTS:
        return BandEnergy(band_code=code, f_low=f_lo, f_high=f_hi, n_points=n)

    n_res = sum(1 for r in resonances_in_band if r["kind"] == "resonance")
    n_anti = sum(1 for r in resonances_in_band if r["kind"] == "anti_resonance")
    return BandEnergy(
        band_code=code,
        f_low=f_lo,
        f_high=f_hi,
        n_points=n,
        rms_db=float(np.sqrt(np.mean(m * m))),
        mean_db=float(np.mean(m)),
        std_db=float(np.std(m, ddof=0)),
        range_db=float(np.max(m) - np.min(m)),
        n_resonances=n_res,
        n_antiresonances=n_anti,
    )


def _resonances_in_band(
    resonances: list[dict], band: Optional[BandSpec]
) -> list[dict]:
    if band is None:
        return resonances
    return [
        r
        for r in resonances
        if band.min_hz <= r["frequency_hz"] <= band.max_hz
    ]


def _resonance_density_per_decade(
    resonances: list[dict], frequency_hz: np.ndarray
) -> float:
    if frequency_hz.size == 0 or not resonances:
        return 0.0
    f_lo = float(frequency_hz.min())
    f_hi = float(frequency_hz.max())
    if f_lo <= 0 or f_hi <= f_lo:
        return 0.0
    decades = math.log10(f_hi) - math.log10(f_lo)
    if decades <= 0:
        return 0.0
    return float(len(resonances) / decades)


def _peak_irregularity_score(resonances: list[dict]) -> float:
    """Coefficient of variation of inter-resonance log-spacings.

    A perfectly regular signature has constant log-spacing (cv → 0).
    Random / disordered signatures have cv > 0.5. Returns a clamped
    value in [0, 1] for ergonomic use in remarks.
    """
    if len(resonances) < 3:
        return 0.0
    log_f = np.log10([r["frequency_hz"] for r in resonances if r["frequency_hz"] > 0])
    diffs = np.diff(np.sort(log_f))
    if diffs.size == 0:
        return 0.0
    mean_d = float(np.mean(diffs))
    if mean_d <= 0:
        return 0.0
    cv = float(np.std(diffs, ddof=0) / mean_d)
    return float(min(max(cv, 0.0), 1.0))


def _noise_estimate(
    frequency_hz: np.ndarray, magnitude_db: np.ndarray
) -> tuple[Optional[float], Optional[float]]:
    """Crude noise-floor + SNR estimate from the very-high-frequency tail.

    Returns ``(noise_floor_db, snr_db)``. If the trace doesn't extend
    above ``_NOISE_FLOOR_HF_HZ``, falls back to the top decade.
    """
    if frequency_hz.size < 50:
        return None, None
    f_max = float(frequency_hz.max())
    cutoff = min(_NOISE_FLOOR_HF_HZ, f_max / math.sqrt(10))
    tail_mask = frequency_hz >= cutoff
    if not np.any(tail_mask):
        # Fallback: top decade
        cutoff = f_max / 10
        tail_mask = frequency_hz >= cutoff
    if not np.any(tail_mask):
        return None, None
    tail = magnitude_db[tail_mask]
    body = magnitude_db[~tail_mask]
    if body.size < 10:
        return float(np.mean(tail)), None
    noise_floor = float(np.median(tail))
    signal_peak = float(np.max(body))
    return noise_floor, float(signal_peak - noise_floor)


def _abnormal_damping_flags(resonances: list[dict]) -> list[str]:
    """Flag suspicious Q-factor patterns."""
    flags: list[str] = []
    qs = [r["q_factor"] for r in resonances if r.get("q_factor") is not None]
    if not qs:
        return flags
    qs_arr = np.asarray(qs, dtype=float)
    if np.any(qs_arr > 200):
        flags.append("Unusually high Q-factor detected — possible measurement artefact")
    if np.median(qs_arr) < 1.5 and len(qs_arr) >= 3:
        flags.append("Median Q-factor very low — heavy damping or measurement noise")
    if qs_arr.max() / max(qs_arr.min(), 0.1) > 50:
        flags.append("Wide spread in Q-factors — non-uniform damping across the signature")
    return flags


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def analyse_standalone(tested: TraceData) -> StandaloneResult:
    """Run the Mode 2 analysis pipeline on a single trace.

    The result carries ``Severity.APPEARS_NORMAL`` when nothing looks
    suspicious, ``Severity.SUSPECT`` when one or more anomaly flags
    fire, and ``Severity.INDETERMINATE`` when the trace is too short or
    too noisy to assess.
    """
    f = tested.frequency_hz
    m = tested.magnitude_db
    notes: list[str] = []

    if f.size < 50:
        return StandaloneResult(
            band_energy=[],
            full_band_energy=BandEnergy(
                band_code="FULL", f_low=None, f_high=None, n_points=int(f.size)
            ),
            resonances=[],
            n_resonances=0,
            n_antiresonances=0,
            resonance_density_per_decade=0.0,
            peak_irregularity_score=0.0,
            noise_floor_db=None,
            snr_estimate_db=None,
            abnormal_damping_flags=[],
            anomaly_flags=["trace_too_short"],
            qualitative_severity=Severity.INDETERMINATE,
            auto_remarks=(
                "Standalone analysis: trace too short to assess "
                f"({f.size} points). Re-run after capturing a full sweep."
            ),
            notes=notes,
        )

    resonances = detect_resonances(f, m)
    n_res = sum(1 for r in resonances if r["kind"] == "resonance")
    n_anti = sum(1 for r in resonances if r["kind"] == "anti_resonance")

    band_energy = []
    for band in BANDS_SPEC_V2:
        be = _band_energy(f, m, band, _resonances_in_band(resonances, band))
        band_energy.append(be)
    full_be = _band_energy(f, m, None, resonances)

    density = _resonance_density_per_decade(resonances, f)
    irregularity = _peak_irregularity_score(resonances)
    noise_floor, snr = _noise_estimate(f, m)
    damping_flags = _abnormal_damping_flags(resonances)

    # ---------- Anomaly logic ----------
    anomalies: list[str] = []

    if density > _RESONANCE_DENSITY_HIGH:
        anomalies.append(
            f"Very dense resonance signature ({density:.1f} peaks/decade) — "
            "possible winding deformation indication (no reference available)"
        )
    elif density < _RESONANCE_DENSITY_LOW and n_res < 3:
        anomalies.append(
            "Sparse resonance signature — verify measurement setup, "
            "low-Q response or compromised excitation"
        )

    if irregularity >= _PEAK_IRREGULARITY_SUSPECT:
        # Locate the worst-affected band.
        worst_band = max(
            band_energy,
            key=lambda b: (b.n_resonances + b.n_antiresonances),
            default=full_be,
        )
        anomalies.append(
            f"Irregular resonance distribution in {worst_band.band_code} region "
            f"(irregularity score {irregularity:.2f})"
        )

    hf_be = next((b for b in band_energy if b.band_code == _HF_BAND), None)
    mid_be = next((b for b in band_energy if b.band_code == _MID_BAND), None)
    if hf_be and hf_be.n_points >= _MIN_BAND_POINTS:
        if hf_be.range_db is not None and hf_be.range_db > 30.0:
            anomalies.append(
                f"Wide HIGH-band magnitude span ({hf_be.range_db:.1f} dB) — "
                "lead/grounding or tap-changer artefacts likely"
            )
    if mid_be and mid_be.n_resonances == 0 and mid_be.n_antiresonances == 0:
        anomalies.append(
            "MID band shows no detectable resonances — check sweep coverage and excitation"
        )

    if snr is not None and snr < 20.0:
        anomalies.append(f"Low signal-to-noise estimate ({snr:.1f} dB) — re-test recommended")

    anomalies.extend(damping_flags)

    # ---------- Severity ----------
    if anomalies:
        severity = Severity.SUSPECT
    else:
        severity = Severity.APPEARS_NORMAL

    # ---------- Auto-remark ----------
    if severity == Severity.APPEARS_NORMAL:
        remark = (
            "Standalone analysis (no reference available). Signature appears "
            f"normal within statistical limits: {n_res} resonances, "
            f"{n_anti} anti-resonances detected at "
            f"{density:.1f} peaks/decade, irregularity {irregularity:.2f}. "
            "Upload a reference trace from the active overhaul cycle to "
            "produce a comparative verdict."
        )
    else:
        bullet_lines = "\n  • ".join(anomalies)
        remark = (
            "Standalone analysis flagged anomalies (no reference available):\n"
            f"  • {bullet_lines}\n"
            "These observations are qualitative — once a reference is uploaded, "
            "comparative metrics (CC / RL / resonance shift) will supersede this remark."
        )

    return StandaloneResult(
        band_energy=band_energy,
        full_band_energy=full_be,
        resonances=resonances,
        n_resonances=n_res,
        n_antiresonances=n_anti,
        resonance_density_per_decade=density,
        peak_irregularity_score=irregularity,
        noise_floor_db=noise_floor,
        snr_estimate_db=snr,
        abnormal_damping_flags=damping_flags,
        anomaly_flags=anomalies,
        qualitative_severity=severity,
        auto_remarks=remark,
        notes=notes,
    )


__all__ = ["analyse_standalone"]
