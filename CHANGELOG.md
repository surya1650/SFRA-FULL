# Changelog

All notable changes to the APTRANSCO SFRA platform. Dates use ISO-8601.
Keep entries newest-first.

## [0.3.0-phase2] · 2026-04-30

### Added — frontend wired to /api/* (Phase 2.1)
- `frontend/src/api/client.ts` — typed fetch wrapper covering all 17
  Phase 1 + 2 endpoints, with `ApiError` carrying status + payload.
- `frontend/src/api/hooks.ts` — TanStack Query hooks for every
  endpoint, with cache-key constants and mutation-side invalidation.
- `frontend/src/components/SfraPlot.tsx` — Plotly.js chart component
  driven by `GET /api/traces/{id}/data`. Lazy-loads Plotly so the
  initial bundle stays small. Magnitude / phase modes, sub-band
  shading, log-scale frequency axis.
- `frontend/src/tabs/DashboardTab.tsx` — replaces mock data with live
  `useHealth()` + `useTransformers()`; shows transformer table.
- `frontend/src/tabs/UploadTab.tsx` — full Phase 2 upload flow:
  register transformer + open cycle + start session + upload file +
  run analysis. Renders `unmapped_sweeps` warnings inline.
- `frontend/src/tabs/TracesTab.tsx` — paste a trace id and the Plotly
  charts render. Phase 3 will add a richer trace selector once the
  session/cycle browser lands.

### Added — reports (Phase 2.2)
- `src/sfra_full/reports/pdf.py` — ReportLab session report.
  - APTRANSCO-letterhead slot (auto-includes `assets/branding/aptransco_logo.{png,jpg,svg}` if present).
  - Cover with nameplate + cycle + session + instrument + ambient.
  - Per-combination pages with the per-band metrics table, Mode 2
    band-energy table, auto + reviewer remarks.
  - Final summary table.
  - **DRAFT — INCOMPLETE watermark** (spec v2 §11) when fewer
    analyses exist than the catalogue's expected total for the type.
- `src/sfra_full/reports/xlsx.py` — openpyxl session workbook:
  - **Summary** sheet (one row per analysis, severity colour-fill).
  - **One sheet per combination** with re-gridded `frequency_hz /
    ref_mag_db / test_mag_db / diff_db / phase` columns so
    APTRANSCO reviewers can plot directly in Excel.
  - **_metadata** sheet capturing the full session context.
- `src/sfra_full/api/routes/reports.py` — `GET /api/sessions/{id}/report.pdf`
  and `.xlsx`. Both render even on partial sets (with watermark).

### Added — auth scaffold (Phase 2.3)
- `src/sfra_full/auth/` — JWT, Engineer/Reviewer/Admin roles, bcrypt
  hashing (direct, not via passlib — passlib's bcrypt backend breaks
  with bcrypt>=4), FastAPI deps for `get_current_user` +
  `require_engineer/reviewer/admin`.
- `src/sfra_full/auth/sso.py` — APTRANSCO SSO placeholder router
  returning 501 until IdP details are confirmed (spec v2 §2 hook).
- `src/sfra_full/api/routes/auth.py` — `POST /api/auth/login`
  (form-encoded), `GET /api/auth/me`, `POST /api/users`, `GET /api/users`.
  Admin endpoints gated on the ADMIN role.
- Permissive email validator that accepts `.test` TLDs (Pydantic's
  `EmailStr` rejects them).
- `alembic/versions/20260430_0002_user_auth.py` — adds the user table.

### Added — integration tests
- `tests/integration/test_reports.py` — PDF endpoint produces a
  well-formed PDF on a partial set; XLSX endpoint produces a workbook
  with Summary + per-combination + _metadata sheets.
- `tests/integration/test_auth.py` — login issues JWT, /me returns
  user, bad password rejected, engineer can't list users (403),
  admin can create + list users, missing Authorization → 401, SSO → 501.

### Test status
- **69 / 69 tests passing**, 80 % coverage on `src/sfra_full/*`.
- API endpoints now total **23**: 16 Phase 1 + 2 reports + 5 auth + 2 SSO placeholders.

### Phase 2 → Phase 3 handoff
Remaining: OEM-specific parsers (Doble / Omicron / CIGRE / IEC / IEEE)
promoted from upstream, THREE_WINDING combination enumeration once
APTRANSCO confirms the row count, real APTRANSCO FRAX fixtures
(12-sweep TWO_WINDING + 22-sweep AUTO_BROUGHT_OUT), real letterhead
asset upload, frontend session/cycle browser + analysis-view 4-panel
plot per spec v2 §10, multi-language support if APTRANSCO requires it.

---

## [0.2.0-phase1] · 2026-04-30

### Added — DB layer
- `src/sfra_full/db/` — SQLAlchemy 2.x typed declarative models for all six
  spec v2 §3 tables: `Transformer`, `OverhaulCycle`, `TestSession`,
  `Combination`, `Trace`, `AnalysisResult`. Naming convention enforced
  for stable Alembic autogenerate.
- `db/enums.py` — `TransformerType`, `InterventionType`, `SessionType`,
  `TraceRole`, `SourceFormat`, `AnalysisModeDB`, `SeverityDB`. Mirrors
  of the analysis-side enums with bidirectional converters.
- `db/array_helpers.py` — numpy ↔ bytes round-trip via `numpy.save`
  (BYTEA columns, spec v2 §3). `allow_pickle=False` always.
- `db/base.py` — declarative `Base`, engine + sessionmaker factories.
  Auto-selects SQLite (default, dev) vs PostgreSQL (prod) based on
  `SFRA_DATABASE_URL`.
- AnalysisResult.mode + .severity stored as enum **values** (via
  `values_callable`) so the CHECK constraint
  `(mode = 'reference_missing_analysis' AND reference_trace_id IS NULL)
   OR (mode = 'comparative' AND reference_trace_id IS NOT NULL)` works.

### Added — storage
- `src/sfra_full/storage/filesystem.py` — `FilesystemStorage` with the
  spec v2 §2 layout (`<serial>/cycle_NNN/<combo>/<role>/<sha8>_<file>`),
  SHA-256 keyed, idempotent on identical content, path-traversal safe.

### Added — Alembic
- `alembic.ini` + `alembic/env.py` + `alembic/versions/20260426_0001_initial.py`
  — first migration emits the full spec v2 §3 schema.

### Added — seeder
- `scripts/seed_combinations.py` — upserts the YAML catalogue (48 rows)
  into the `combination` table. Idempotent.

### Added — FastAPI app + 16 routes
- `src/sfra_full/api/app.py` — `create_app(database_url, storage_root,
  create_schema)` factory. Wires DB engine + filesystem storage onto
  `app.state` so tests can inject custom values.
- `src/sfra_full/api/routes/health.py` — `GET /api/health`.
- `src/sfra_full/api/routes/standards.py` — `GET /api/standards/{combinations,bands}`,
  with YAML fallback when the DB hasn't been seeded yet.
- `src/sfra_full/api/routes/transformers.py` — `POST/GET /api/transformers`,
  `GET /api/transformers/{id}`, `POST/GET /api/transformers/{id}/cycles`.
  Opening a new cycle auto-closes the prior open cycle (spec v2 §3
  invariant: at most one open cycle per transformer).
- `src/sfra_full/api/routes/sessions.py` — `POST /api/transformers/{id}/sessions`,
  `GET /api/sessions/{id}`, `POST /api/sessions/{id}/upload`. The upload
  endpoint handles BOTH spec v2 §6.1 paths in one route:
    - **Single-trace**: caller passes `combination_code` form param.
    - **Batch FRAX**: caller leaves it empty; the parser auto-explodes
      and the resolver maps each sweep. Sweeps that don't resolve are
      reported in `unmapped_sweeps` with their suggested code.
- `src/sfra_full/api/routes/traces.py` — `GET /api/traces/{id}` (metadata)
  and `GET /api/traces/{id}/data` (decoded numpy arrays for plotting).
- `src/sfra_full/api/routes/analyses.py` — `POST /api/sessions/{id}/analyse`
  iterates every TESTED trace, finds its REFERENCE counterpart in the
  active cycle (matched by combination_id), and dispatches to Mode 1 or
  Mode 2. Idempotent — re-running supersedes previous results.

### Added — CLI
- `sfra-full seed-db [--database-url]` — run the seeder.
- `sfra-full serve [--host --port --reload]` — run uvicorn dev server.

### Added — integration tests
- `tests/integration/test_db.py` — schema build, FK enforcement, the
  full Transformer → OverhaulCycle → TestSession → Trace chain, seeder.
- `tests/integration/test_storage.py` — filesystem layout, SHA-256
  idempotency, path-traversal safety.
- `tests/integration/test_api.py` — full §6 flow:
  - Health, standards fallback to YAML.
  - Transformer CRUD + duplicate-serial conflict.
  - Cycle auto-close on new open.
  - **Spec v2 §6.2 invariant**: tested-only upload → Mode 2; reference
    arrival in same cycle → re-analyse switches to Mode 1.
  - Unmapped sweep reporting (no fail).
  - Trace data decode.

### Test status
- **61 / 61 tests passing**, 79 % coverage on `src/sfra_full/*`.
- 16 API endpoints registered, OpenAPI schema published at `/openapi.json`.

### Phase 1 → Phase 2 handoff
Remaining for Phase 2: frontend wiring to `/api/*`, PDF/XLSX report
generators, auth (JWT + Engineer/Reviewer/Admin), OEM-specific parsers,
THREE_WINDING combination enumeration, real APTRANSCO FRAX fixtures.

---

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
