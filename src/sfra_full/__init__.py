"""APTRANSCO SFRA analysis platform.

Top-level package for the SFRA Diagnostic Tool. Submodules:

- ``sfra_full.sfra_analysis`` — pure analysis primitives (Mode 1 comparison
  and Mode 2 standalone), orchestrator, parsers, verdict engine.
- ``sfra_full.api`` — FastAPI app and routes.
- ``sfra_full.db`` — SQLAlchemy models + Alembic migrations.
- ``sfra_full.parsers`` — file format parsers (FRAX/CSV/Doble/Generic).
- ``sfra_full.reports`` — PDF + XLSX report generation.
- ``sfra_full.storage`` — filesystem trace blob storage with SHA-256.
- ``sfra_full.cli`` — command-line entry points (``sfra-full ...``).

Spec source of truth: ``standards/ieee_c57_149_combinations.yaml``.
Design system: ``docs/design/DESIGN_SYSTEM.md``.
"""
from __future__ import annotations

__version__ = "0.1.0-phase0"
__all__ = ["__version__"]
