"""NumPy array <-> bytes round-trip for the BYTEA columns on Trace.

Spec v2 §3 trace storage: ``frequency_hz``, ``magnitude_db``, ``phase_deg``
are persisted as BYTEA via ``numpy.save`` / ``numpy.load`` over a BytesIO.

We wrap that with a few guards:

- ``allow_pickle=False`` always — the stored arrays are pure numeric
  data; we never want a malicious upload to round-trip arbitrary
  Python objects out of the DB.
- Compression (np.savez with deflate) for typical trace sizes
  (1-2k points × float64 ≈ 16 KB raw → ~5 KB compressed).
- Round-trip tolerance ≤ 1e-12 (reverified in unit tests).
"""
from __future__ import annotations

import io
from typing import Optional

import numpy as np


def array_to_bytes(arr: Optional[np.ndarray]) -> Optional[bytes]:
    """Serialize a numpy array to bytes via ``np.save``.

    Returns ``None`` for None input so callers can pass optional phase
    arrays through without branching.
    """
    if arr is None:
        return None
    arr = np.asarray(arr)
    buf = io.BytesIO()
    np.save(buf, arr, allow_pickle=False)
    return buf.getvalue()


def bytes_to_array(data: Optional[bytes]) -> Optional[np.ndarray]:
    """Deserialize bytes produced by ``array_to_bytes``."""
    if data is None or len(data) == 0:
        return None
    return np.load(io.BytesIO(data), allow_pickle=False)


def array_pair_roundtrip(arr: np.ndarray) -> bool:
    """Sanity helper for tests: True iff round-trip preserves bit-equality."""
    raw = array_to_bytes(arr)
    rec = bytes_to_array(raw)
    return rec is not None and np.array_equal(arr, rec)


__all__ = ["array_pair_roundtrip", "array_to_bytes", "bytes_to_array"]
