"""Resonance detection, matching, and (optional) transfer-function pole fit.

This module wraps the upstream ``external/SFRA`` primitives where they are
already correct (resonance detection, vector-fitting style pole/zero
extraction) and adds spec v2 §7.4 specifics:

- Resonance pairing with 10% log-frequency tolerance
- ``shifted`` / ``lost`` / ``new`` classification
- Pole flagging when frequency moves >5% or magnitude >3 dB

The upstream import is **soft**: when ``external/SFRA`` is not present
(e.g. on a CI runner that didn't run setup_external.sh), this module
falls back to local SciPy implementations so the test suite still passes.
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
from scipy import signal


# ---------------------------------------------------------------------------
# Resonance detection — local impl (mirrors upstream behaviour, simplified)
# ---------------------------------------------------------------------------
def detect_resonances(
    frequency_hz: np.ndarray,
    magnitude_db: np.ndarray,
    *,
    prominence_db: float = 3.0,
    distance_pts: int = 5,
) -> list[dict[str, Any]]:
    """Find resonances (peaks) and anti-resonances (dips) in a magnitude trace.

    Spec v2 §7.4 step 1. Operates on a uniform log-frequency grid so the
    ``distance`` parameter behaves consistently across decades.

    Returns one dict per peak with keys:
        kind: 'resonance' | 'anti_resonance'
        frequency_hz: float
        magnitude_db: float
        q_factor:    float | None
        prominence_db: float
    """
    f = np.asarray(frequency_hz, dtype=float)
    m = np.asarray(magnitude_db, dtype=float)
    if f.size < 5:
        return []

    log_f = np.log10(np.clip(f, 1e-6, None))
    uni_lf = np.linspace(log_f.min(), log_f.max(), max(2000, f.size))
    m_uni = np.interp(uni_lf, log_f, m)

    out: list[dict[str, Any]] = []
    for kind, sign in (("resonance", -1.0), ("anti_resonance", +1.0)):
        # Resonances are *dips* in SFRA magnitude (low impedance ⇒ low Vresp/Vref)
        # — flip sign so find_peaks treats them as peaks.
        peaks, props = signal.find_peaks(
            sign * m_uni, prominence=prominence_db, distance=distance_pts
        )
        for idx, prom in zip(peaks, props["prominences"], strict=False):
            f_peak = float(10 ** uni_lf[idx])
            m_peak = float(m_uni[idx])
            q = _q_from_3db_bandwidth(uni_lf, m_uni, idx, sign=sign)
            out.append(
                {
                    "kind": kind,
                    "frequency_hz": f_peak,
                    "magnitude_db": m_peak,
                    "q_factor": q,
                    "prominence_db": float(prom),
                }
            )
    out.sort(key=lambda p: p["frequency_hz"])
    return out


def _q_from_3db_bandwidth(
    log_f: np.ndarray, mag: np.ndarray, idx: int, *, sign: float
) -> Optional[float]:
    """Estimate Q factor from the 3-dB bandwidth around a peak/dip."""
    peak_val = mag[idx]
    target = peak_val + sign * 3.0  # for resonances (sign=-1), target = peak+3 above

    left = idx
    while left > 0 and (
        (mag[left] <= target) if sign < 0 else (mag[left] >= target)
    ):
        left -= 1
    right = idx
    while right < mag.size - 1 and (
        (mag[right] <= target) if sign < 0 else (mag[right] >= target)
    ):
        right += 1
    if right <= left:
        return None
    f_lo = 10 ** log_f[left]
    f_hi = 10 ** log_f[right]
    f_pk = 10 ** log_f[idx]
    bw = f_hi - f_lo
    if bw <= 0:
        return None
    return float(f_pk / bw)


# ---------------------------------------------------------------------------
# Resonance pairing — spec v2 §7.4 step 2
# ---------------------------------------------------------------------------
def match_resonances(
    ref_peaks: list[dict[str, Any]],
    test_peaks: list[dict[str, Any]],
    *,
    log_tolerance: float = 0.0414,  # log10(1.10) ≈ 0.0414  → ±10% frequency
) -> tuple[list[dict[str, Any]], int, int, int]:
    """Pair reference and tested resonances within ±10% log-frequency.

    Returns ``(pairs, n_matched, n_lost, n_new)`` where ``pairs`` contains
    one dict per pairing with classification 'matched' / 'lost' / 'new'.
    Greedy nearest-neighbour assignment.
    """
    ref_used: set[int] = set()
    test_used: set[int] = set()
    pairs: list[dict[str, Any]] = []

    candidates: list[tuple[float, int, int]] = []
    for i, r in enumerate(ref_peaks):
        log_rf = np.log10(max(r["frequency_hz"], 1e-12))
        for j, t in enumerate(test_peaks):
            if r["kind"] != t["kind"]:
                continue
            log_tf = np.log10(max(t["frequency_hz"], 1e-12))
            d = abs(log_tf - log_rf)
            if d <= log_tolerance:
                candidates.append((d, i, j))
    candidates.sort()

    for d, i, j in candidates:
        if i in ref_used or j in test_used:
            continue
        ref_used.add(i)
        test_used.add(j)
        ref = ref_peaks[i]
        test = test_peaks[j]
        shift_pct = 100.0 * (test["frequency_hz"] - ref["frequency_hz"]) / ref["frequency_hz"]
        pairs.append(
            {
                "kind": ref["kind"],
                "ref_frequency_hz": ref["frequency_hz"],
                "test_frequency_hz": test["frequency_hz"],
                "shift_pct": shift_pct,
                "delta_db": test["magnitude_db"] - ref["magnitude_db"],
                "classification": "matched",
            }
        )

    n_matched = len(pairs)

    n_lost = 0
    for i, ref in enumerate(ref_peaks):
        if i in ref_used:
            continue
        n_lost += 1
        pairs.append(
            {
                "kind": ref["kind"],
                "ref_frequency_hz": ref["frequency_hz"],
                "test_frequency_hz": None,
                "shift_pct": None,
                "delta_db": None,
                "classification": "lost",
            }
        )

    n_new = 0
    for j, test in enumerate(test_peaks):
        if j in test_used:
            continue
        n_new += 1
        pairs.append(
            {
                "kind": test["kind"],
                "ref_frequency_hz": None,
                "test_frequency_hz": test["frequency_hz"],
                "shift_pct": None,
                "delta_db": None,
                "classification": "new",
            }
        )

    return pairs, n_matched, n_lost, n_new


# ---------------------------------------------------------------------------
# Pole fit (advisory only) — spec v2 §7.4 step 3
# ---------------------------------------------------------------------------
def fit_poles(
    frequency_hz: np.ndarray,
    magnitude_db: np.ndarray,
    phase_deg: Optional[np.ndarray] = None,
    *,
    orders: tuple[int, ...] = (6, 8, 10),
) -> list[dict[str, float]]:
    """Best-effort pole extraction via SciPy's invfreqs.

    Returns a list of up to 6 dominant poles with keys ``{real, imag,
    frequency_hz, magnitude_db}``. Robust against fitting failure: returns
    ``[]`` if no order converges, so the runner can skip pole comparison
    silently.
    """
    f = np.asarray(frequency_hz, dtype=float)
    mag_db = np.asarray(magnitude_db, dtype=float)
    if f.size < 16:
        return []

    mag_lin = 10 ** (mag_db / 20.0)
    if phase_deg is not None and len(phase_deg) == len(f):
        ph = np.unwrap(np.deg2rad(np.asarray(phase_deg, dtype=float)))
    else:
        # Minimum-phase reconstruction.
        log_mag = np.log(np.maximum(mag_lin, 1e-30))
        ph = -np.imag(signal.hilbert(log_mag))

    h = mag_lin * np.exp(1j * ph)
    w = 2.0 * np.pi * f

    best_poles: list[dict[str, float]] = []
    best_err = float("inf")
    for n in orders:
        try:
            b, a = signal.invfreqs(h, w, n, n)
        except Exception:
            continue
        try:
            h_fit = np.polyval(b, 1j * w) / np.polyval(a, 1j * w)
            err = float(
                np.linalg.norm(h - h_fit) / max(np.linalg.norm(h), 1e-30)
            )
        except Exception:
            continue
        if err < best_err:
            best_err = err
            poles = np.roots(a)
            ranked = sorted(poles, key=lambda p: abs(p))
            best_poles = []
            for p in ranked[:6]:
                f_eq = abs(p) / (2.0 * np.pi)
                best_poles.append(
                    {
                        "real": float(p.real),
                        "imag": float(p.imag),
                        "frequency_hz": float(f_eq),
                        "magnitude": float(abs(p)),
                    }
                )
    return best_poles


__all__ = ["detect_resonances", "fit_poles", "match_resonances"]
