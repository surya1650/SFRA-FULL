# Changelog

All notable changes to the APTRANSCO SFRA platform. Dates use ISO-8601.
Keep entries newest-first.

## [0.1.0-phase0] · 2026-04-25 to 2026-04-26

### Added — Phase 0 foundations
- Repository scaffold: `src/sfra_full/`, `tests/`, `standards/`, `docs/`,
  `frontend/`, `data/`, `assets/branding/`, `external/`.
- `pyproject.toml` (uv-managed), `.pre-commit-config.yaml`, `Makefile`,
  `scripts/setup_external.sh`, `scripts/validate_catalogue.py`.
- `standards/ieee_c57_149_combinations.yaml` — single source of truth for
  the IEEE C57.149-2012 combination catalogue. Spec v2 layout: 4 transformer
  types, 48 explicit combinations:
  - `TWO_WINDING` = 15
  - `AUTO_WITH_TERTIARY_BROUGHT_OUT` = 21
  - `AUTO_WITH_TERTIARY_BURIED` = 12
  - `THREE_WINDING` = pending Phase 1 engineering review
  - Includes spec v2 §7.2 bands (LOW/MID_L/MID/HIGH) and DL/T 911
    sub-bands (RLW/RLM/RLH) + threshold table.
- Design system handoff (Claude Design bundle) copied to `docs/design/`
  and `frontend/src/styles/design-tokens.css`. 7-tab UI prototype + 13
  component preview cards + colour/type/spacing tokens (Inter +
  JetBrains Mono, Tailwind blue brand, slate neutrals, semantic verdict
  colours, dark mode).
- `external/SFRA/` cloned (gitignored — read-only managed dependency).
  Setup script keeps the local copy at a pinned SHA when
  `external/SFRA.sha` is present.
- `REFACTOR_MAP.md` — keep / wrap / rewrite / new ledger against every
  primitive in the upstream repo.
- `docs/DECISIONS.md` — engineering choices and divergences from defaults.

### Added — analysis core (`src/sfra_full/sfra_analysis/`)
- `bands.py` — loads the YAML catalogue's spec_v2 + DL/T 911 bands as
  immutable `BandSpec` objects. Provides `mask`, `slice`, `overlap_range`.
- `result_types.py` — dataclass envelope `AnalysisOutcome` with two modes
  (`comparative`, `reference_missing_analysis`). Per-band `BandIndices`,
  Mode 2 `BandEnergy`, `Severity` enum spanning Mode 1 + Mode 2 ladders.
- `resample.py` — spec v2 §7.1 PCHIP re-grid onto 1000-point log axis,
  `InsufficientOverlapError` when overlap < 80%.
- `statistical.py` — spec v2 §7.3 verbatim metrics: uncentered CC, ASLE,
  uncentered CSD, MM, max-deviation, RL factor with CC ≤ 0.99999 clamp.
- `verdict.py` — DL/T 911 RL → severity mapping per band, worst-of-bands
  aggregator, spec v2 §7.7 auto-remarks templates with band-specific root-
  cause hints.
- `transfer.py` — peak detection (resonance + anti-resonance with Q-factor
  estimation), greedy ±10% log-frequency pairing → matched/lost/new,
  pole fit via `scipy.signal.invfreqs` order search.
- `standalone.py` — **NEW** Mode 2: band energy distribution, resonance
  density per decade, peak irregularity (cv of inter-peak log-spacing),
  noise-floor + SNR estimate from the HF tail, abnormal-damping flags,
  qualitative severity (APPEARS_NORMAL / SUSPECT / INDETERMINATE) with
  self-analysis remark templates.
- `compare.py` — Mode 1 single-pair orchestrator. Combines per-band RL
  severity with resonance-shift geometry severity (resonance-only
  max_shift, anti-resonances excluded as noise-prone) and takes the worst.
- `runner.py` — top-level dispatcher: `run(tested, reference=None)` →
  `AnalysisOutcome`. Spec v2 §6.2 invariant lives here.

### Added — file parsers (`src/sfra_full/sfra_analysis/io/`)
- `base.py` — common `ParsedSweep` dataclass with combination_code, tap
  positions, instrument metadata, source format/file.
- `combination_resolver.py` — FRAX `<Properties>` → spec v2 §5
  combination_code mapping. Phase aliases (R/S/T ↔ 1U/1V/1W ↔ U/V/W ↔
  A/B/C). Shorted-terminal classification (LV vs TV → `_TVS` suffix).
- `frax.py` — handles the real MEGGER `<Frameworx>/<Frax>/<TestRecord>/<Sweep>`
  schema (spec v2 §4.1 verbatim — semicolon-row, 7-field-row data block,
  V_resp/V_ref → dB conversion, phase_a unwrap) AND the legacy
  `<FRAXFile>/<Measurement>/<Point>` schema (used by upstream's synthetic
  fixtures). Placeholder sweeps dropped silently.
- `csv.py` — auto-detects delimiter (`, ; \t`), Hz vs kHz, deg vs rad,
  optional header row.
- `dispatch.py` — extension + magic-byte routing.

### Added — CLI
- `sfra-full analyse <tested> [--reference <path>] [--out <json>]` runs
  the runner end-to-end.
- `sfra-full frax-info <path>` lists all sweeps in a FRAX file with
  resolved combination codes.
- `sfra-full validate-catalogue` runs the YAML schema validator.
- `sfra-full version` prints the engine version.

### Added — tests
- `tests/conftest.py` — `synthetic_trace_factory` fixture.
- 44 unit tests across `tests/unit/test_{catalogue,bands,statistical,
  resample,runner,standalone,io}.py`. All passing.
- 75% coverage on `src/sfra_full/sfra_analysis/*`.
- Phase 0 §10 gate: `python3 -m pytest tests/` is green.

### Verified end-to-end
- Parses `external/SFRA/backend/samples/ref.frax` and `test.frax`
  (synthetic upstream fixtures, 401 points each).
- Mode 1 detects the upstream's deliberate 3% resonance shift and emits
  `MINOR_DEVIATION` with the spec v2 auto-remark.
- Mode 2 on a single trace produces a qualitative analysis with no
  reference, including resonance count, density, irregularity score, and
  band-energy distribution.

### Known gaps (Phase 1+)
- DB layer (SQLAlchemy 2.x + Alembic), storage, FastAPI routes, frontend
  Vite skeleton, PDF/XLSX reports, auth, OEM-specific parsers (Doble /
  Omicron / CIGRE / IEC / IEEE), THREE_WINDING combination enumeration,
  real APTRANSCO FRAX fixtures (12-sweep TWO_WINDING + 22-sweep
  AUTO_BROUGHT_OUT). All tracked in `REFACTOR_MAP.md` §4.
