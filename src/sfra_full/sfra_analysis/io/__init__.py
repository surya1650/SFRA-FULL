"""SFRA file format parsers.

Spec v2 §4 enumerates four formats:

    .frax           MEGGER FRAX XML — primary, fully specified (4.1)
    .csv / .tsv     Generic tabular (4.2)
    .xfra           Doble M5400 / M5300 (4.3)
    .xml/.fra/.sfra Schema-flexible generic XML (4.4)

All parsers emit ``ParsedSweep`` containers with the same shape so the
downstream analysis runner doesn't need to know which format produced a
given trace.
"""
from __future__ import annotations

from .base import ParsedSweep
from .combination_resolver import resolve_combination_code
from .dispatch import parse_file
from .frax import parse_frax
from .csv import parse_csv

__all__ = [
    "ParsedSweep",
    "parse_csv",
    "parse_file",
    "parse_frax",
    "resolve_combination_code",
]
