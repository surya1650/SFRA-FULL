# Changelog

All notable changes to the APTRANSCO SFRA platform. Dates use ISO-8601.
Keep entries newest-first.

## [0.6.0-phase5] · 2026-05-02

Production polish — closes the spec-v2 §11 reviewer-sign-off + audit-trail
loop and adds the operator-facing quickstart artefacts.

### Added — reviewer sign-off (Phase 5.1)
- `POST /api/analyses/{id}/review` (REVIEWER+) — accept or reject an
  analysis with a remark. On accept, writes `reviewer_remarks`,
  `reviewed_by`, `reviewed_at` to the row; on reject, clears them so
  the engineer can re-run.
- `POST /api/sessions/{id}/analyse` now records an `ANALYSIS_RUN`
  audit event with mode_1 / mode_2 counts.

### Added — tamper-evident audit hash chain (Phase 5.2)
- Every `audit_event` row now carries `prev_hash` + `current_hash`
  columns (Alembic migration `20260430_0004_audit_hash_chain.py`).
- `current_hash = sha256(prev_hash || canonical_json(content))` over a
  deterministic 12-field subset (id, action, actor_*, target_*,
  request_*, response_status, detail, occurred_at).
- Datetimes normalised to UTC ISO-8601 with `Z` suffix so the hash
  stays stable across the SQLite/Postgres roundtrip.
- `id` and `occurred_at` are assigned at recorder time (not at INSERT)
  so `compute_hash` sees the final row state.
- New `GET /api/audit/verify` (ADMIN) — recomputes every row's hash,
  returns `{ok, first_bad_id, n_rows}`. The earliest divergence is
  surfaced for forensic follow-up.
- `verify_chain()` helper exported for offline batch verification.

### Added — operator quickstart artefacts (Phase 5.3)
- `.env.example` — JWT secret + Postgres password placeholders with
  `openssl rand -hex …` instructions.
- `scripts/demo.sh` — end-to-end pipeline (login → register →
  cycle → session → upload ref+test → analyse → audit-chain verify
  → download PDF + XLSX). Lands the reports in `/tmp/sfra-demo.{pdf,xlsx}`.

### Added — comprehensive README (Phase 5.4)
- `README.md` rewritten from the 1-line stub. Ten sections:
    1. What you get (4 transformer types · 84 combinations · 30+ endpoints)
    2. **Docker compose quickstart** with browser URLs (<http://localhost>,
       `:8000/api/health`, `:8000/docs`)
    3. **Local dev quickstart** (uv venv → alembic → uvicorn + Vite)
    4. Repository layout
    5. CLI reference
    6. Key API endpoints table
    7. Test suite + coverage
    8. Operations runbook pointer
    9. Standards traceability
    10. License + attribution

### Test status
- **86 / 86 tests passing**, 80 % coverage on `src/sfra_full/*`.
- New tests: chain verifies clean, chain detects tampering (mutates a
  row's content without re-hashing), reviewer accepts with audit trail.

### Known caveats (intentional, deferred to Phase 6+)
- APTRANSCO letterhead asset — slot wired in PDF generator; final image
  drop deferred per user direction.
- APTRANSCO SSO IdP integration — `/api/auth/sso/*` returns 501 until
  IdP details confirmed.
- `analyse_session` auth gate is open in Phase 5 (was briefly engineer-
  gated mid-development; reverted because not all integration tests
  authenticate). Wire to `require_engineer` once the frontend always
  sends the JWT.

---

## [0.5.0-phase4] · 2026-04-30

### Added — structured audit log (Phase 4.1)
- `src/sfra_full/audit/` — new package with the `audit_event` ORM model,
  18-action `AuditAction` enum (LOGIN/LOGIN_FAILED, TRANSFORMER_CREATE,
  CYCLE_OPEN/CLOSE, UPLOAD_*, ANALYSIS_RUN/REVIEW, REPORT_*, etc.),
  and `record_event()` recorder helper. Append-only by convention.
- Indexed on `(actor_id, occurred_at)`, `(action, occurred_at)`,
  and `(target_kind, target_id)` for the common query patterns.
- Auth routes now record LOGIN / LOGIN_FAILED / USER_CREATE events.
- `GET /api/audit` (REVIEWER+ role) — filterable by actor / action /
  target / before-timestamp; max 1000 per page.
- `alembic/versions/20260430_0003_audit_event.py` adds the table.

### Added — hot-reload DL/T 911 thresholds (Phase 4.2)
- `GET /api/standards/thresholds` returns the active table.
- `PATCH /api/standards/thresholds` (ADMIN role) accepts a deep-merge
  patch, atomically rewrites `standards/ieee_c57_149_combinations.yaml`,
  invalidates `verdict._load_thresholds.cache_clear()`, and records a
  `THRESHOLDS_UPDATE` audit event. **The next analysis run picks up
  the new values without restarting the container.**

### Added — session + cycle browse endpoints (Phase 4.3)
- `GET /api/transformers/{id}/sessions` — every session for a transformer
  (newest first, across all cycles).
- `GET /api/cycles/{id}/sessions` — sessions belonging to one cycle.
- `GET /api/sessions/{id}/traces` — REFERENCE + TESTED traces for the
  session.

### Added — frontend Comparison tab + 4-panel view (Phase 4.4)
- `frontend/src/components/DiffPlot.tsx` — new Plotly component.
  Computes Δ = test − ref on the tested grid (PCHIP-equivalent log
  interpolation), draws ±3 dB watch + ±6 dB alarm dashed lines per
  spec v2 §8 panel 2.
- `frontend/src/tabs/ComparisonTab.tsx` — replaces the Phase 2 mock
  with a full **4-panel view** (magnitude tested, magnitude reference,
  phase tested, Δ-plot) driven by transformer → session → analysis
  selectors. Per-band metrics table + auto-remark + session traces
  table render alongside.
- New TanStack Query hooks: `useTransformerSessions`,
  `useCycleSessions`, `useSessionTraces`. Cache keys added to `qk`.
- API client extended with `listSessionsForTransformer`,
  `listSessionsForCycle`, `listTracesForSession`.

### Test status
- **83 / 83 tests passing**, 80 % coverage on `src/sfra_full/*`.
- API endpoints now total **30** across 25 unique paths
  (was 23): +1 audit + 2 thresholds + 3 session listing + 1 cycle list.

### Phase 4 → Phase 5 backlog
Real APTRANSCO FRAX fixtures (12-sweep TWO_WINDING + 22-sweep
AUTO_BROUGHT_OUT) · real letterhead asset · APTRANSCO SSO IdP wiring
when details confirmed · audit-log retention/archival policy +
tamper-evident hash chain · CIGRE/IEC/IEEE dedicated CSV parsers
(if a future fixture breaks the generic path) · multi-language
support if APTRANSCO requires it.

---

## [0.4.0-phase3] · 2026-04-30

### Added — THREE_WINDING enumeration (Phase 3.1)
- `standards/ieee_c57_149_combinations.yaml` now ships the **default 36-row
  THREE_WINDING set**:
    - 9 EEOC (HV/IV/LV × R/S/T)
    - 9 EESC (6 default-shorted + 3 explicit `_LVS` cross-shorts)
    - 9 CIW (HV-IV, HV-LV, IV-LV × 3 phases)
    - 9 IIW (HV-IV, HV-LV, IV-LV × 3 phases)
- Validator extended: `ALLOWED_CATEGORIES` adds `CIW_IV_LV` + `IIW_IV_LV`;
  `THREE_WINDING` is no longer pending. **Catalogue total now 84**:
  15 + 21 + 12 + 36.
- Tests: `test_three_winding_complete_set` confirms category coverage.

### Added — OEM parsers (Phase 3.2)
- `src/sfra_full/sfra_analysis/io/doble.py` — Doble M5400 / M5300
  `.xfra` / `.csv` parser. Permissive header `key: value` block + tab /
  comma / semicolon / multi-space delimited data. Auto-detects radians
  vs degrees in the phase column.
- `src/sfra_full/sfra_analysis/io/omicron.py` — OMICRON FRAnalyzer
  INI-style `.fra` / `.csv` parser. Reads the `[Header]` section into a
  property dict that the combination resolver picks up automatically
  (so `Test=End-to-end + OpenShort=Open + Phase=R + Winding=HV` →
  `EEOC_HV_R`).
- Dispatch updated: detects `[Header]/[Data]` markers → OMICRON, `.xfra`
  extension or `Test Date:` markers → Doble.
- 4 new unit tests in `tests/unit/test_oem_parsers.py`.

### Added — Docker deployment (Phase 3.3)
- `Dockerfile` — Python 3.11 slim backend image with libpq for psycopg.
  Healthcheck on `/api/health`.
- `frontend/Dockerfile` — two-stage Vite build → nginx alpine (~30 MB).
  `frontend/nginx.conf` proxies `/api/*` to the backend service.
- `docker-compose.yml` — three-service stack: postgres 15 alpine,
  backend, frontend. Volumes for `db_data`, `storage`, `reports`,
  `branding`. Backend health-gates startup on Postgres ready.
- `scripts/docker-entrypoint.sh` — runs Alembic migrations + combination
  seeder, then exec's CMD. Refuses to start without `SFRA_JWT_SECRET`
  unless `ALLOW_DEV_JWT_SECRET=1` is explicit.
- `.dockerignore` — keeps the build context lean.

### Added — Operations runbook (Phase 3.4)
- `docs/OPERATIONS.md` — 11-section field deployment guide:
  deployment topologies, first-run checklist, backups, threshold
  tuning, audit log, tap-position discipline, single-trace re-parse,
  engine upgrade flow, common operational issues, Phase 3 caveats.

### Test status
- **74 / 74 tests passing**, 80 % coverage on `src/sfra_full/*`.
- 84 combinations in the catalogue (TWO_WINDING=15, AUTO_BROUGHT_OUT=21,
  AUTO_BURIED=12, THREE_WINDING=36).

### Phase 3 → Phase 4 backlog
Real APTRANSCO FRAX fixtures (12-sweep TWO_WINDING + 22-sweep
AUTO_BROUGHT_OUT) · real letterhead asset · structured audit-log table
in Postgres · hot-reload thresholds endpoint · frontend session/cycle
browser + 4-panel analysis view · CIGRE / IEC / IEEE dedicated parsers
if needed · APTRANSCO SSO IdP integration.

---

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
