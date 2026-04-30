"""MEGGER FRAX (.frax) XML parser — spec v2 §4.1.

The FRAX file is a single XML document containing one or more <Sweep>
elements. Each sweep has:

    <n>                  — human-readable label
    <Ident>              — UUID
    <Properties>         — Test / OpenShort / Phase / Winding / Tap / etc.
    <BandSettings>       — start/stop frequency, points-per-decade
    <s>                  — instrument self-description
    <Data>               — semicolon-delimited rows, comma-delimited fields:
                            f, V_ref, V_resp, mag_lin, im, phase_a_rad, phase_b_rad

Conversions (spec v2 §4.1):
    magnitude_db = 20 * log10(field_3 = mag_lin)
    phase_deg    = field_5 (rad) * 180 / π, then numpy.unwrap

Sweeps with empty Properties or no <Data> child are silently skipped
(spec v2 §4.1: "real files have placeholder rows; the parser drops them").

Uses the stdlib ``xml.etree.ElementTree`` — works without lxml installed,
which keeps the substation-laptop install footprint small. lxml support
can be added later as a perf optimisation; the API is identical.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Optional, Union
from xml.etree import ElementTree as ET

import numpy as np

from .base import ParsedSweep
from .combination_resolver import resolve_combination_code


def parse_frax(
    source: Union[str, bytes, Path],
    *,
    source_filename: Optional[str] = None,
) -> list[ParsedSweep]:
    """Parse a FRAX file. Accepts a path, bytes, or an XML string.

    Returns one ``ParsedSweep`` per non-placeholder <Sweep> in the file.
    Placeholder sweeps (empty Properties, no <Data>) are dropped silently.
    """
    if isinstance(source, (str, Path)) and not _looks_like_xml(str(source)):
        path = Path(source)
        text = path.read_text(encoding="utf-8", errors="replace")
        filename = source_filename or path.name
    elif isinstance(source, bytes):
        text = _decode(source)
        filename = source_filename or ""
    else:
        text = str(source)
        filename = source_filename or ""

    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid FRAX XML: {exc}") from exc

    nameplate_meta = _extract_nameplate(root)

    sweeps: list[ParsedSweep] = []
    for elem in root.iter("Sweep"):
        parsed = _parse_one_sweep(elem, nameplate_meta, filename)
        if parsed is not None:
            sweeps.append(parsed)

    # Fallback: simpler <FRAXFile>/<Measurement>/<Point> schema used by the
    # upstream synthetic samples and by some legacy FRAX exports. We accept
    # this so tests against external/SFRA/backend/samples/*.frax pass
    # without separate fixture generation.
    if not sweeps:
        sweeps.extend(_parse_legacy_measurements(root, filename, nameplate_meta))
    return sweeps


def _parse_legacy_measurements(
    root: ET.Element, filename: str, nameplate_meta: dict[str, Any]
) -> list[ParsedSweep]:
    """Handle simplified FRAX with <Measurement><Point freq= mag= phase=/></Measurement>."""
    out: list[ParsedSweep] = []
    # Pull header-style metadata (different schema than <Nameplate>).
    header_meta: dict[str, Any] = dict(nameplate_meta)
    header = root.find(".//Header")
    if header is not None:
        for child in header:
            if child.text and child.text.strip():
                header_meta[child.tag] = child.text.strip()

    for measurement in root.iter("Measurement"):
        freqs: list[float] = []
        mags_db: list[float] = []
        phases_deg: list[float] = []
        for p in measurement.findall("Point"):
            f = p.get("freq") or p.findtext("freq")
            m = p.get("mag") or p.findtext("mag")
            ph = p.get("phase") or p.findtext("phase")
            if f is None or m is None:
                continue
            try:
                freqs.append(float(f))
                mags_db.append(float(m))
                if ph is not None:
                    phases_deg.append(float(ph))
            except ValueError:
                continue
        if not freqs:
            continue
        f_arr = np.asarray(freqs, dtype=float)
        m_arr = np.asarray(mags_db, dtype=float)
        p_arr: Optional[np.ndarray] = None
        if len(phases_deg) == len(freqs):
            p_arr = np.unwrap(np.deg2rad(np.asarray(phases_deg, dtype=float)))
            p_arr = p_arr * 180.0 / math.pi

        label = (
            measurement.get("name")
            or measurement.findtext("Name")
            or measurement.findtext("Label")
            or "measurement"
        )
        # Legacy schema doesn't carry full FRAX <Properties>, but we
        # surface header values + tag the source format clearly.
        out.append(
            ParsedSweep(
                label=str(label),
                frequency_hz=f_arr,
                magnitude_db=m_arr,
                phase_deg=p_arr,
                properties=dict(header_meta),
                combination_code=None,
                tap_current=header_meta.get("Tap"),
                instrument_metadata={"nameplate": nameplate_meta},
                raw_header="",
                source_format="FRAX_LEGACY",
                source_file=filename,
            )
        )
    return out


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------
def _looks_like_xml(s: str) -> bool:
    return s.lstrip().startswith("<")


def _decode(content: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _extract_nameplate(root: ET.Element) -> dict[str, Any]:
    np_node = root.find(".//Nameplate")
    if np_node is None:
        return {}
    out: dict[str, Any] = {}
    for tag in (
        "Date", "Time", "Location", "SerialNumber", "Year", "Phase",
        "KV1", "MVA1", "Tester", "AmbientTemp", "TopOilTemp",
    ):
        text = np_node.findtext(tag)
        if text and text.strip():
            out[tag] = text.strip()
    return out


def _parse_properties(sweep: ET.Element) -> dict[str, str]:
    return {
        (p.get("name") or ""): (p.text or "").strip()
        for p in sweep.findall(".//Properties/Property")
    }


def _parse_instrument(sweep: ET.Element) -> dict[str, str]:
    s_node = sweep.find(".//s")
    if s_node is None:
        return {}
    out: dict[str, str] = {}
    for tag in ("Serial", "CalibrateDate", "PCSW", "SystemSW", "SystemHW", "SystemFPGA"):
        text = s_node.findtext(tag)
        if text and text.strip():
            out[tag] = text.strip()
    return out


def _parse_data_block(text: str) -> tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]:
    """Parse the FRAX Data text block.

    Returns (frequency_hz, magnitude_db, phase_deg_or_None).
    """
    rows = [r for r in text.split(";") if r.strip()]
    freqs: list[float] = []
    mags_db: list[float] = []
    phases_rad: list[float] = []
    have_phase = True
    for row in rows:
        fields = row.split(",")
        if len(fields) < 4:
            continue
        try:
            f = float(fields[0])
            mag_lin = float(fields[3])
        except (ValueError, IndexError):
            continue
        if mag_lin <= 0 or not math.isfinite(mag_lin):
            continue
        freqs.append(f)
        mags_db.append(20.0 * math.log10(mag_lin))
        # Spec v2 §4.1: prefer phase_a (field 5). field index 5 (0-based).
        if len(fields) >= 6:
            try:
                phases_rad.append(float(fields[5]))
            except ValueError:
                have_phase = False
        else:
            have_phase = False

    f_arr = np.asarray(freqs, dtype=float)
    m_arr = np.asarray(mags_db, dtype=float)
    if have_phase and len(phases_rad) == len(freqs):
        p_arr = np.unwrap(np.asarray(phases_rad, dtype=float)) * 180.0 / math.pi
    else:
        p_arr = None
    return f_arr, m_arr, p_arr


def _parse_one_sweep(
    sweep: ET.Element, nameplate_meta: dict[str, Any], filename: str
) -> Optional[ParsedSweep]:
    properties = _parse_properties(sweep)
    if not properties or not properties.get("Test"):
        # Placeholder sweep — spec v2 §4.1 says drop silently.
        return None

    data_node = sweep.find("Data")
    if data_node is None or not (data_node.text or "").strip():
        return None

    f_arr, m_arr, p_arr = _parse_data_block(data_node.text or "")
    if f_arr.size == 0:
        return None

    label = (
        sweep.findtext("n")
        or sweep.get("name")
        or properties.get("Test", "Sweep")
    )

    combo_code = resolve_combination_code(properties)

    return ParsedSweep(
        label=label.strip(),
        frequency_hz=f_arr,
        magnitude_db=m_arr,
        phase_deg=p_arr,
        properties=dict(properties),
        combination_code=combo_code,
        tap_current=properties.get("Tap") or None,
        tap_previous=properties.get("Previous Tap") or None,
        detc_tap=properties.get("DETC tap position") or None,
        instrument_metadata={
            **_parse_instrument(sweep),
            "nameplate": nameplate_meta,
        },
        raw_header="",
        source_format="FRAX",
        source_file=filename,
    )


__all__ = ["parse_frax"]
