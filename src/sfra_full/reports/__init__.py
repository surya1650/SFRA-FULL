"""Report generators — PDF (ReportLab) + XLSX (openpyxl).

Spec v2 §10:
    - PDF cover with APTRANSCO letterhead + nameplate + session metadata
    - One PDF page per combination (4-panel plot + metrics table + remarks)
    - PDF summary table at the end with overall verdict = worst-of-bands
    - XLSX mirroring the PDF + per-combination data sheets

Spec v2 §11 non-blocking rule: when the catalogue is partially populated
(some combinations unanalysed), reports are still generated but carry a
prominent ``DRAFT — INCOMPLETE`` watermark and the missing rows are
highlighted in red.
"""
from __future__ import annotations

from .pdf import build_session_pdf, PdfRenderOptions
from .xlsx import build_session_xlsx

__all__ = ["build_session_pdf", "build_session_xlsx", "PdfRenderOptions"]
