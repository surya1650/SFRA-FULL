"""PDF report generator — ReportLab.

Per spec v2 §10. Generates one PDF for a TestSession including:

- Cover page with APTRANSCO letterhead slot, transformer nameplate,
  session metadata, instrument details, ambient conditions, overall
  verdict (worst-of-all-combinations).
- One page per analysed combination with the metrics table, resonance
  shifts, and the auto-remark.
- Final summary table.
- DRAFT watermark when some combinations remain unanalysed.

The letterhead asset is read from ``assets/branding/aptransco_logo.*``
when present; if not, a clean default cover with the APTRANSCO name is
rendered (per the user's design-question answer).
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from sfra_full import __version__
from sfra_full.db import (
    AnalysisResult,
    Combination,
    OverhaulCycle,
    TestSession,
    Trace,
    Transformer,
)
from sfra_full.db.enums import severity_from_db


_ASSETS_DIR = Path(__file__).resolve().parents[3] / "assets" / "branding"


_VERDICT_COLOURS = {
    "NORMAL": colors.HexColor("#10b981"),
    "MINOR_DEVIATION": colors.HexColor("#f59e0b"),
    "SIGNIFICANT_DEVIATION": colors.HexColor("#f97316"),
    "SEVERE_DEVIATION": colors.HexColor("#f43f5e"),
    "APPEARS_NORMAL": colors.HexColor("#10b981"),
    "SUSPECT": colors.HexColor("#f59e0b"),
    "INDETERMINATE": colors.HexColor("#94a3b8"),
}

_SEVERITY_RANK = [
    "SEVERE_DEVIATION",
    "SIGNIFICANT_DEVIATION",
    "MINOR_DEVIATION",
    "SUSPECT",
    "NORMAL",
    "APPEARS_NORMAL",
    "INDETERMINATE",
]


@dataclass(slots=True)
class PdfRenderOptions:
    title: str = "APTRANSCO SFRA Diagnostic Report"
    notes: str = ""
    include_letterhead: bool = True


def _logo_path() -> Optional[Path]:
    """Return the first ReportLab-renderable letterhead asset, if present.

    ReportLab's ``Image`` flowable doesn't render SVG without ``svglib``,
    which we don't carry as a runtime dep. So when the only logo on disk
    is the SVG recreation (committed at ``assets/branding/aptransco_logo.svg``),
    we skip it and let the cover render with the text-only APTRANSCO
    title instead. Drop a real PNG/JPG into the same folder to upgrade.
    """
    if not _ASSETS_DIR.exists():
        return None
    for ext in (".png", ".jpg", ".jpeg"):
        cand = _ASSETS_DIR / f"aptransco_logo{ext}"
        if cand.exists():
            return cand
    return None


def _worst_severity(severities: Sequence[str]) -> str:
    if not severities:
        return "INDETERMINATE"
    for level in _SEVERITY_RANK:
        if level in severities:
            return level
    return "INDETERMINATE"


def _draft_watermark(canvas: Canvas, doc) -> None:  # noqa: ARG001
    """Draw the DRAFT — INCOMPLETE watermark across the page."""
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#dc2626"))
    canvas.setFont("Helvetica-Bold", 64)
    canvas.translate(A4[0] / 2, A4[1] / 2)
    canvas.rotate(40)
    canvas.setFillAlpha(0.12)
    canvas.drawCentredString(0, 0, "DRAFT — INCOMPLETE")
    canvas.restoreState()


def build_session_pdf(
    *,
    transformer: Transformer,
    cycle: OverhaulCycle,
    session: TestSession,
    analyses: list[AnalysisResult],
    combinations: list[Combination],
    expected_total: int,
    options: Optional[PdfRenderOptions] = None,
) -> bytes:
    """Render a session PDF and return its bytes.

    ``expected_total`` comes from the YAML catalogue's per-type ``total``
    so we can detect partial populations and stamp the DRAFT watermark.
    """
    opts = options or PdfRenderOptions()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm,
        topMargin=1.6 * cm, bottomMargin=1.6 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title", parent=styles["Title"], textColor=colors.HexColor("#1e3a8a")
    )
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], textColor=colors.HexColor("#1e3a8a"))

    story: list = []
    is_partial = len(analyses) < expected_total

    # ---------- Cover ----------
    if opts.include_letterhead:
        logo = _logo_path()
        if logo:
            try:
                story.append(Image(str(logo), width=4 * cm, height=4 * cm))
            except Exception:
                pass
    story.append(Paragraph(opts.title, title_style))
    story.append(Spacer(1, 0.4 * cm))
    story.append(
        Paragraph(
            f"Generated {datetime.now(tz=timezone.utc).isoformat()} · "
            f"engine v{__version__}",
            styles["Italic"],
        )
    )
    story.append(Spacer(1, 0.4 * cm))

    nameplate = [
        ["Transformer serial", transformer.serial_no],
        ["Type", transformer.transformer_type.value],
        ["Vector group", transformer.vector_group or "—"],
        ["MVA / HV / LV / TV", _ratings_line(transformer)],
        ["Manufacturer / Year", f"{transformer.manufacturer or '—'} / {transformer.year_of_manufacture or '—'}"],
        ["Substation / Bay", f"{transformer.substation or '—'} / {transformer.feeder_bay or '—'}"],
        ["Overhaul cycle", f"#{cycle.cycle_no} ({cycle.intervention_type.value}) — {cycle.cycle_start_date}"],
        ["Session", f"{session.session_type.value} on {session.session_date}"],
        ["Tested by / Witnessed", f"{session.tested_by or '—'} / {session.witnessed_by or '—'}"],
        ["Ambient °C / Oil °C / Humidity %",
         f"{session.ambient_temp_c or '—'} / {session.oil_temp_c or '—'} / {session.humidity_pct or '—'}"],
        ["Instrument", f"{session.instrument_make_model or '—'} (s/n {session.instrument_serial or '—'})"],
        ["Calibration due", str(session.instrument_calibration_due_date) if session.instrument_calibration_due_date else "—"],
    ]
    np_table = Table(nameplate, colWidths=[5.5 * cm, 11.5 * cm])
    np_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e2e8f0")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ]
        )
    )
    story.append(np_table)
    story.append(Spacer(1, 0.5 * cm))

    severities = [a.severity.value for a in analyses]
    overall = _worst_severity(severities)
    bg = _VERDICT_COLOURS.get(overall, colors.grey)
    story.append(
        Paragraph(
            f"<para backcolor='{bg.hexval()}' textColor='#ffffff' alignment='center'>"
            f"<b>Overall session verdict: {overall}</b></para>",
            styles["BodyText"],
        )
    )
    story.append(Spacer(1, 0.3 * cm))
    if is_partial:
        story.append(
            Paragraph(
                f"<font color='#dc2626'><b>DRAFT — INCOMPLETE:</b> "
                f"{len(analyses)} of {expected_total} catalogue combinations analysed.</font>",
                styles["BodyText"],
            )
        )

    if opts.notes:
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph(f"<b>Notes:</b> {opts.notes}", styles["BodyText"]))

    story.append(PageBreak())

    # ---------- Per-combination pages ----------
    code_to_combo = {c.id: c for c in combinations}
    for ar in sorted(analyses, key=lambda a: (a.combination_id or 0)):
        combo = code_to_combo.get(ar.combination_id) if ar.combination_id else None
        story.append(
            Paragraph(
                f"Combination: <b>{combo.code if combo else 'unmapped'}</b> · "
                f"mode={ar.mode.value} · "
                f"<font color='{_VERDICT_COLOURS.get(ar.severity.value, colors.grey).hexval()}'>"
                f"<b>{ar.severity.value}</b></font>",
                h2,
            )
        )
        story.append(Spacer(1, 0.2 * cm))

        if ar.indicators_json:
            per_band = ar.indicators_json.get("per_band") or []
            if per_band:
                rows = [["Band", "CC", "RL", "ASLE", "CSD", "MaxΔ (dB)", "MaxΔ (Hz)", "n_pts"]]
                for b in per_band:
                    rows.append([
                        b.get("band_code", "?"),
                        _fmt(b.get("cc"), 4),
                        _fmt(b.get("rl_factor"), 2),
                        _fmt(b.get("asle"), 3),
                        _fmt(b.get("csd"), 3),
                        _fmt(b.get("max_dev_db"), 2),
                        _fmt_freq(b.get("max_dev_freq_hz")),
                        str(b.get("n_points", "—")),
                    ])
                tbl = Table(rows, colWidths=[2*cm, 1.8*cm, 1.5*cm, 1.7*cm, 1.7*cm, 2.2*cm, 2.2*cm, 1.5*cm])
                tbl.setStyle(_table_style())
                story.append(tbl)
                story.append(Spacer(1, 0.3 * cm))

        if ar.standalone_json:
            be = ar.standalone_json.get("band_energy") or []
            if be:
                story.append(Paragraph("<b>Band energy (Mode 2 standalone)</b>", styles["Heading4"]))
                rows = [["Band", "RMS (dB)", "Mean (dB)", "Std (dB)", "Range (dB)", "Resonances"]]
                for b in be:
                    rows.append([
                        b.get("band_code", "?"),
                        _fmt(b.get("rms_db"), 2),
                        _fmt(b.get("mean_db"), 2),
                        _fmt(b.get("std_db"), 2),
                        _fmt(b.get("range_db"), 2),
                        str(b.get("n_resonances", 0)),
                    ])
                tbl = Table(rows, colWidths=[2*cm, 2*cm, 2*cm, 2*cm, 2*cm, 2.5*cm])
                tbl.setStyle(_table_style())
                story.append(tbl)
                story.append(Spacer(1, 0.3 * cm))

        if ar.auto_remarks:
            story.append(Paragraph("<b>Auto-remark</b>", styles["Heading4"]))
            story.append(Paragraph(ar.auto_remarks, styles["BodyText"]))
            story.append(Spacer(1, 0.3 * cm))
        if ar.reviewer_remarks:
            story.append(Paragraph("<b>Reviewer remark</b>", styles["Heading4"]))
            story.append(Paragraph(ar.reviewer_remarks, styles["BodyText"]))
        story.append(PageBreak())

    # ---------- Summary table ----------
    story.append(Paragraph("Session summary", h2))
    sum_rows = [["Combination", "Mode", "Severity", "n_matched", "n_lost", "n_new", "Auto-remark"]]
    for ar in analyses:
        combo = code_to_combo.get(ar.combination_id) if ar.combination_id else None
        ind = ar.indicators_json or {}
        sum_rows.append([
            combo.code if combo else "—",
            ar.mode.value,
            ar.severity.value,
            str(ind.get("n_matched", "—")),
            str(ind.get("n_lost", "—")),
            str(ind.get("n_new", "—")),
            (ar.auto_remarks or "")[:80],
        ])
    if len(sum_rows) == 1:
        story.append(
            Paragraph(
                "No analyses recorded for this session yet.", styles["BodyText"]
            )
        )
    else:
        st = Table(sum_rows, colWidths=[3*cm, 3*cm, 3*cm, 1.5*cm, 1.5*cm, 1.5*cm, 4*cm])
        st.setStyle(_table_style())
        story.append(st)

    if is_partial:
        doc.build(story, onFirstPage=_draft_watermark, onLaterPages=_draft_watermark)
    else:
        doc.build(story)
    return buf.getvalue()


def _ratings_line(t: Transformer) -> str:
    parts = []
    if t.nameplate_mva is not None:
        parts.append(f"{t.nameplate_mva} MVA")
    if t.hv_kv is not None:
        parts.append(f"HV {t.hv_kv} kV")
    if t.lv_kv is not None:
        parts.append(f"LV {t.lv_kv} kV")
    if t.tv_kv is not None:
        parts.append(f"TV {t.tv_kv} kV")
    return " · ".join(parts) or "—"


def _fmt(v, digits: int = 4) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):.{digits}f}"
    except (TypeError, ValueError):
        return "—"


def _fmt_freq(v) -> str:
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    if f >= 1_000_000:
        return f"{f/1e6:.2f} MHz"
    if f >= 1_000:
        return f"{f/1e3:.1f} kHz"
    return f"{f:.0f} Hz"


def _table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ]
    )


__all__ = ["PdfRenderOptions", "build_session_pdf"]
