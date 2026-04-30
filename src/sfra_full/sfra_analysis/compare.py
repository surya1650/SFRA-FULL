"""Mode 1 — full comparative analysis (reference + tested).

Spec v2 §7.5: ``compare(reference_trace, tested_trace) -> AnalysisResult``.

Pipeline:
    1. Resample both onto a common log-frequency grid (resample.regrid_pair).
    2. Compute per-band statistical indices (statistical.all_bands).
    3. Detect resonances on both, match within ±10% log-frequency.
    4. Fit poles (advisory) for both, flag shifted poles.
    5. Map RL factors → per-band severity → overall severity.
    6. Render auto-remarks.

Single-pair function — no batch state. Spec v2 §6.2 invariant: "uploading
one combination must produce the same plots and metrics as uploading
twenty" is enforced by keeping this function reference-clean.
"""
from __future__ import annotations

import numpy as np

from .resample import regrid_pair


def _resonance_shift_severity(
    *, max_shift_pct: float, n_lost: int, n_new: int
) -> Severity:
    """Map resonance-pair geometry to a severity escalation.

    Heuristic (tunable; see DECISIONS.md):
        n_lost+n_new ≥ 3 OR max_shift > 10%   → SEVERE
        n_lost+n_new ≥ 1 OR max_shift > 5%    → SIGNIFICANT
        max_shift > 2%                        → MINOR
        otherwise                             → NORMAL
    """
    disrupted = n_lost + n_new
    if disrupted >= 3 or max_shift_pct > 10.0:
        return Severity.SEVERE_DEVIATION
    if disrupted >= 1 or max_shift_pct > 5.0:
        return Severity.SIGNIFICANT_DEVIATION
    if max_shift_pct > 2.0:
        return Severity.MINOR_DEVIATION
    return Severity.NORMAL
from .result_types import (
    ComparativeResult,
    ResonancePair,
    Severity,
    TraceData,
)
from .statistical import all_bands
from .transfer import detect_resonances, fit_poles, match_resonances
from .verdict import render_remarks, severity_for_rl, worst_severity


def compare(reference: TraceData, tested: TraceData) -> ComparativeResult:
    """Run the full Mode 1 pipeline. Returns a populated ComparativeResult."""
    pair = regrid_pair(
        reference.frequency_hz,
        reference.magnitude_db,
        tested.frequency_hz,
        tested.magnitude_db,
        phase_ref_deg=reference.phase_deg,
        phase_test_deg=tested.phase_deg,
    )

    per_band, full_band = all_bands(
        pair.frequency_hz, pair.ref_magnitude_db, pair.test_magnitude_db
    )

    band_severity: dict[str, Severity] = {}
    for bi in per_band:
        band_severity[bi.band_code] = severity_for_rl(bi.band_code, bi.rl_factor)
    full_severity = severity_for_rl(full_band.band_code, full_band.rl_factor)

    rl_overall = worst_severity(list(band_severity.values()) + [full_severity])

    # Resonance detection on the original (un-regridded) traces preserves
    # the instrument's native sampling for peak finding; comparison happens
    # against the test trace's resonances directly.
    ref_peaks = detect_resonances(reference.frequency_hz, reference.magnitude_db)
    test_peaks = detect_resonances(tested.frequency_hz, tested.magnitude_db)
    pairs_raw, n_matched, n_lost, n_new = match_resonances(ref_peaks, test_peaks)
    pairs = [ResonancePair(**p) for p in pairs_raw]

    # Anti-resonance peak finding is noisier (broader peaks, more
    # detection variance) so we use only resonance pairs for the strict
    # severity escalation. Anti-resonance shifts are still reported for
    # human review.
    max_shift = max(
        (
            abs(p.shift_pct)
            for p in pairs
            if p.shift_pct is not None and p.kind == "resonance"
        ),
        default=0.0,
    )

    # Spec v2 §7.4: resonance-shift / lost / new escalates severity beyond
    # what RL alone would conclude. The uncentered CC is dB-similarity
    # tolerant; resonance-pair geometry is the spec-grade frequency-shift
    # signal. Combine both, take the worst.
    shift_severity = _resonance_shift_severity(
        max_shift_pct=max_shift, n_lost=n_lost, n_new=n_new
    )
    overall = worst_severity([rl_overall, shift_severity])

    # Poles (advisory)
    poles_ref = fit_poles(
        reference.frequency_hz, reference.magnitude_db, reference.phase_deg
    )
    poles_test = fit_poles(
        tested.frequency_hz, tested.magnitude_db, tested.phase_deg
    )

    remarks = render_remarks(
        per_band,
        full_band,
        band_severity,
        overall,
        n_lost=n_lost,
        n_new=n_new,
        n_shifts=n_matched,
        max_shift_pct=max_shift,
    )

    return ComparativeResult(
        band_indices=per_band,
        full_band_indices=full_band,
        resonances_ref=ref_peaks,
        resonances_test=test_peaks,
        resonance_pairs=pairs,
        n_matched=n_matched,
        n_lost=n_lost,
        n_new=n_new,
        poles_ref=poles_ref,
        poles_test=poles_test,
        band_severity=band_severity,
        overall_severity=overall,
        auto_remarks=remarks,
    )


__all__ = ["compare"]
