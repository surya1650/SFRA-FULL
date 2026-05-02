"""Tests for the Doble + OMICRON OEM parsers."""
from __future__ import annotations

from sfra_full.sfra_analysis.io import parse_doble, parse_file, parse_omicron


# ---------------------------------------------------------------------------
# Doble
# ---------------------------------------------------------------------------
DOBLE_SAMPLE = b"""Test Date: 2024-04-15
Transformer: TR-A1
Winding: HV
Phase: A
Tap: 5

Frequency Hz\tMagnitude dB\tPhase deg
20\t-23.45\t-89.12
100\t-22.10\t-87.50
1000\t-19.80\t-65.00
10000\t-25.40\t-30.00
100000\t-40.10\t10.00
1000000\t-55.20\t40.00
"""


def test_doble_parses_header_and_data():
    sweeps = parse_doble(DOBLE_SAMPLE, source_filename="tr-a1.xfra")
    assert len(sweeps) == 1
    s = sweeps[0]
    assert s.source_format == "XFRA"
    assert s.frequency_hz.size == 6
    assert s.magnitude_db[0] == -23.45
    assert s.phase_deg is not None
    assert "TR-A1" in s.label
    assert s.tap_current == "5"


def test_doble_dispatched_via_extension():
    fmt, sweeps = parse_file(DOBLE_SAMPLE, source_filename="tr-a1.xfra")
    assert fmt == "DOBLE"
    assert len(sweeps) == 1


# ---------------------------------------------------------------------------
# OMICRON
# ---------------------------------------------------------------------------
OMICRON_SAMPLE = b"""[Header]
Transformer=TR-B2
Winding=HV
Phase=R
Test=End-to-end
OpenShort=Open
Tap=Nominal

[Data]
Frequency,Magnitude,Phase
20,-23.0,-89.0
100,-22.0,-87.0
1000,-19.0,-65.0
10000,-25.0,-30.0
100000,-40.0,10.0
1000000,-55.0,40.0
"""


def test_omicron_parses_sections():
    sweeps = parse_omicron(OMICRON_SAMPLE, source_filename="tr-b2.fra")
    assert len(sweeps) == 1
    s = sweeps[0]
    assert s.source_format == "FRA"
    assert s.frequency_hz.size == 6
    assert s.combination_code == "EEOC_HV_R"  # resolver picks it up
    assert s.tap_current == "Nominal"


def test_omicron_dispatched_via_section_marker():
    fmt, sweeps = parse_file(OMICRON_SAMPLE, source_filename="x.fra")
    assert fmt == "OMICRON"
    assert sweeps[0].combination_code == "EEOC_HV_R"
