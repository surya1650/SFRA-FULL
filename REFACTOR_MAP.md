# REFACTOR_MAP — APTRANSCO SFRA platform

Spec v2 §12 priority deliverable. Maps every primitive in the upstream
`https://github.com/surya1650/SFRA.git` repo (cloned at `external/SFRA/`)
to one of four actions for the new platform:

- **KEEP**    — import verbatim, no refactor
- **WRAP**    — import core; wrap with new orchestration layer
- **REWRITE** — replace with spec-v2-compliant version
- **NEW**     — net-new module, no upstream counterpart

Branch: `claude/sfra-analysis-platform-9F8RS`. Phase 0 status at the bottom.

---

## 1. Backend modules

### 1.1 Parsers (`external/SFRA/backend/parsers/`)

| Upstream file | Action | New location | Notes |
|---|---|---|---|
| `parsers/base.py` | **REWRITE** | `src/sfra_full/sfra_analysis/io/base.py` | Spec v2 §4 demands a richer `ParsedSweep` shape (combination_code, tap_current/previous, detc_tap, instrument_metadata). Upstream's `ParsedTrace` is a leaner subset — replaced. |
| `parsers/factory.py` | **REWRITE** | `src/sfra_full/sfra_analysis/io/dispatch.py` | New name + simpler dispatch (extension + magic). Upstream registry pattern is preserved in spirit. |
| `parsers/frax.py` | **REWRITE** | `src/sfra_full/sfra_analysis/io/frax.py` | Upstream is permissive but doesn't implement the spec v2 §4.1 `<Frameworx>/<Frax>/<TestRecord>/<Sweep>/<Properties>/<Data>` schema. New parser handles BOTH the real schema AND the legacy `<FRAXFile>/<Measurement>/<Point>` (upstream synthetic samples) so test fixtures keep working. |
| `parsers/csv.py` (`parsers/generic.py`, `parsers/tabular.py`) | **REWRITE** | `src/sfra_full/sfra_analysis/io/csv.py` | Spec v2 §4.2: auto-detect Hz/kHz, deg/rad, header presence. Upstream lacks the kHz auto-detect. |
| `parsers/doble.py`, `omicron.py`, `cigre.py`, `iec.py`, `ieee.py` | **DEFERRED** | — | Phase 2 work. The upstream implementations remain available via `external/SFRA` for prototyping; they become NEW entries under `io/` when promoted. |
| **NEW** | — | `src/sfra_full/sfra_analysis/io/combination_resolver.py` | Spec v2 §4.1 FRAX-Property→`combination_code` mapper. Single source of truth used by FRAX parser AND by manual-assign endpoints. |

### 1.2 Analysis core (`external/SFRA/backend/analysis/`)

| Upstream file | Action | New location | Notes |
|---|---|---|---|
| `analysis/indices.py` | **REWRITE** | `src/sfra_full/sfra_analysis/statistical.py` | Spec v2 §7.3 CC formula is **uncentered** cosine similarity. Upstream uses Pearson (mean-centered). The two are NOT equivalent on non-zero-mean dB inputs — see `docs/DECISIONS.md`. ASLE/CSD definitions also differ slightly (upstream uses `np.std(diff, ddof=1)`; spec v2 uses `sqrt(sum(d²)/(N-1))` with no centering). RL factor `RLx = -log10(1-CC)` is brand new. |
| `analysis/resonance.py` | **WRAP** | `src/sfra_full/sfra_analysis/transfer.py` (`detect_resonances`, `match_resonances`) | Upstream's peak finding + greedy matching is solid; ported verbatim with the spec v2 §7.4 ±10% log-tolerance and `lost`/`new`/`matched` classification. |
| `analysis/subbands.py` | **REWRITE** | `src/sfra_full/sfra_analysis/bands.py` | Single source of truth is now the YAML catalogue (`standards/ieee_c57_149_combinations.yaml`). Bands are loaded from there, not hard-coded. |
| `analysis/transfer.py`, `analysis/transfer_function.py` | **WRAP** | `src/sfra_full/sfra_analysis/transfer.py` (`fit_poles`) | Upstream's Sanathanan-Koerner LSTSQ pole fitter is used; spec v2 §7.4 calls for `scipy.signal.invfreqs` order auto-search — implemented locally with that primitive. Pole-shift flagging at >5% magnitude / >3 dB is new. |
| `analysis/standards.py` | **REWRITE** | (later) | Spec v2 §7.3 thresholds come from `dl_t_911_thresholds` in the YAML catalogue. Upstream's three-standard table will become a runtime override file under `data/thresholds/` later. |
| `analysis/classification.py` | **WRAP** | `src/sfra_full/sfra_analysis/verdict.py` | Refactored as a deterministic `severity_for_rl(band, rl)` function + auto-remarks template renderer per spec v2 §7.7. Upstream's monolithic `classify_condition` becomes the orchestrator's role. |
| `analysis/failure_modes.py` | **DEFERRED** | — | Phase 2. The heuristic probability scoring is good but spec v2 wants an `@rule`-decorated registry. Will be promoted into `verdict.py` as `failure_rules.py` when needed. |
| `analysis/circuit_model.py` | **DEFERRED** | — | Spec v2 §11 "Modeling" UI tab calls for ladder-network RLC fitting; upstream has it. Phase 3 work. |
| **NEW** | — | `src/sfra_full/sfra_analysis/standalone.py` | **Mode 2 — single-trace analysis** (no upstream equivalent). Per the user directive: band energy, resonance density, peak irregularity, noise/SNR, abnormal damping → qualitative severity + auto-remark. |
| **NEW** | — | `src/sfra_full/sfra_analysis/result_types.py` | Spec v2 §3 `AnalysisResult` columns + Mode 2 `StandaloneResult` + unified `AnalysisOutcome` envelope. |
| **NEW** | — | `src/sfra_full/sfra_analysis/runner.py` | The Mode 1 / Mode 2 dispatcher. **Spec v2 §6.2 invariant lives here**: a single tested trace MUST always produce a full result. |
| **NEW** | — | `src/sfra_full/sfra_analysis/resample.py` | Spec v2 §7.1: PCHIP onto 1000-pt log grid, refuse comparison if overlap < 80%. Upstream uses `np.interp` on a non-PCHIP grid. |
| **NEW** | — | `src/sfra_full/sfra_analysis/compare.py` | Mode 1 orchestrator — single function `compare(reference, tested) → ComparativeResult`. |

### 1.3 Storage / models / API (`external/SFRA/backend/{models,storage,main}.py`)

| Upstream file | Action | New location | Notes |
|---|---|---|---|
| `storage.py` | **REWRITE** | `src/sfra_full/storage/` (Phase 2) | Upstream is in-memory only. Spec v2 §3 demands SQLite (dev) / PostgreSQL (prod) with raw bytes + SHA-256 in DB. |
| `models.py` (Pydantic) | **WRAP** | `src/sfra_full/api/schemas.py` (Phase 2) | Upstream's Pydantic models are good API DTOs and will be reused with minor renaming for the new ENUMs (REFERENCE/TESTED roles, OverhaulCycle, etc.). |
| `main.py` (FastAPI app) | **REWRITE** | `src/sfra_full/api/app.py` + routers (Phase 2) | Spec v2 §11 needs richer endpoints: per-combination upload, batch FRAX explode, OverhaulCycle CRUD, single-trace Mode 2. |
| `report.py` | **WRAP** | `src/sfra_full/reports/pdf.py` (Phase 3) | ReportLab structure stays. New layout: per-combination pages + APTRANSCO letterhead slot + DRAFT watermark when partial. |

### 1.4 Tests

| Upstream | Action | New |
|---|---|---|
| `external/SFRA/backend/tests/*` | **REUSE LOGIC** | `tests/unit/` | Upstream's test ideas (resonance shift, sub-band classification, parser smoke) feed our spec v2 tests but the new metric formulas mean the numerical assertions are recomputed. |

### 1.5 Frontend (`external/SFRA/frontend/src/`)

The upstream frontend is a working React + Vite + Tailwind + Plotly app
with components that map cleanly to spec v2 §11 UI requirements. The
**design system handoff** (in `docs/design/`) mocks an extended 7-tab
version with the same primitives.

| Upstream component | Action | New location |
|---|---|---|
| `App.jsx` | **REWRITE** | `frontend/src/App.tsx` (TypeScript port + 7-tab nav per design system) |
| `components/SfraPlot.jsx` | **WRAP** | `frontend/src/components/SfraPlot.tsx` (Plotly.js via `react-plotly.js`) |
| `components/ComparisonPanel.jsx` | **WRAP** | `frontend/src/components/ComparisonTable.tsx` |
| `components/SeverityDashboard.jsx` | **WRAP** | `frontend/src/components/SeverityHeader.tsx` (gradient header from design system) |
| `components/FailureModePanel.jsx` | **DEFERRED** | Phase 3 |
| `components/PoleZeroPlot.jsx`, `EquivalentCircuitPanel.jsx`, `TransferFunctionPanel.jsx` | **DEFERRED** | Phase 3 — Modeling tab |
| `components/FileUpload.jsx` | **REWRITE** | `frontend/src/components/UploadModal.tsx` (with mandatory tap-position fields per spec v2 §6.1) |
| `components/StandardsPanel.jsx`, `ThresholdSettingsPanel.jsx` | **WRAP** | Phase 2 admin panel |
| **NEW** | — | `frontend/src/components/CombinationGrid.tsx` | Per-transformer grid with cell-by-cell Mode 1/Mode 2 status lights — implements the §11 status enum (No Data / Only Tested / Reference Available / Fully Analysed). |
| **NEW** | — | `frontend/src/styles/design-tokens.css` | Verbatim from `docs/design/` — Inter/JetBrains Mono, Tailwind blue scale, slate neutrals, semantic verdicts. |

---

## 2. Design system integration

`docs/design/` holds the verbatim Claude Design handoff bundle:

- `README.md` — bundle instructions
- `DESIGN_SYSTEM.md` — full specification (color tokens, typography, components, dark mode, iconography)
- `chat-transcript.md` — design intent ("built from `surya1650/SFRA` repo")
- `ui-kit-prototype.html` — interactive 7-tab React prototype (reference only)
- `preview/*.html` — 13 component preview cards
- `SKILL.md` — design skill manifest

`frontend/src/styles/design-tokens.css` is the production-bound CSS custom
properties file (copied from `docs/design/colors_and_type.css`). Tailwind
will import these via `@import` in `frontend/src/index.css`.

**Verdict naming alignment** (DECISIONS.md records this):

| Spec v2 §3 enum | Design-system verdict color |
|---|---|
| `NORMAL` | `good` (emerald) |
| `MINOR_DEVIATION` | `marginal` (amber) |
| `SIGNIFICANT_DEVIATION` | `moderate` (orange) |
| `SEVERE_DEVIATION` | `bad` (rose) |
| (reserved) | `critical` (red) |
| Mode 2 `APPEARS_NORMAL` | `good` (emerald) |
| Mode 2 `SUSPECT` | `marginal` (amber) |
| Mode 2 `INDETERMINATE` | `unknown` (slate) |

---

## 3. Mode 1 / Mode 2 split

Per the user's directive (this session), the analysis runner accepts a
single tested trace with no reference and produces a full standalone
analysis result. When a reference becomes available later, Mode 1 replaces
Mode 2 automatically. Implementation:

```
src/sfra_full/sfra_analysis/runner.py     ← dispatcher (8 LOC)
                ├─→ compare.py            ← Mode 1 (reference + tested)
                └─→ standalone.py         ← Mode 2 (tested only)
```

Both produce an `AnalysisOutcome` with `mode ∈ {comparative, reference_missing_analysis}`.
DB and report layers consume the outcome envelope only — they don't need
to know which mode produced the result.

---

## 4. What's MISSING vs spec v2 (Phase 1+ work)

1. **DB layer** — SQLAlchemy 2.x models for Transformer / OverhaulCycle / TestSession / Combination / Trace / AnalysisResult; Alembic migrations; SQLite dev / PostgreSQL prod. (Phase 1)
2. **Storage layer** — filesystem trace blob storage with SHA-256 keying (`storage/<serial>/<cycle>/<combo>/<role>/`). Pluggable S3 backend behind the same interface. (Phase 1)
3. **FastAPI routes** — register / overhaul / session / upload (single & batch FRAX) / analyse / report. (Phase 2)
4. **Background tasks** — re-run pending Mode 2 analyses through Mode 1 when a reference is uploaded. (Phase 2)
5. **Frontend** — Vite + React + TS + Tailwind skeleton with the 7 design-system tabs; CombinationGrid; UploadModal; SeverityHeader. (Phase 2-3)
6. **PDF / XLSX reports** — APTRANSCO letterhead slot, per-combination page set, summary table, DRAFT watermark for partial sets. (Phase 3)
7. **Auth** — JWT + Engineer/Reviewer/Admin roles; APTRANSCO SSO hook in `auth/sso.py`. (Phase 3)
8. **OEM parsers** — Doble / Omicron / CIGRE / IEC / IEEE specific paths re-promoted from `external/SFRA`. (Phase 2)
9. **THREE_WINDING combinations** — currently `pending_enumeration: true` in YAML; APTRANSCO engineering must confirm the canonical row count and code list. (Phase 1, blocks UI)
10. **Real APTRANSCO FRAX fixtures** — the 12-sweep TWO_WINDING file and the 22-sweep AUTO_BROUGHT_OUT file referenced in spec v2 §13. Currently testing against synthetic upstream samples. Once provided, drop into `tests/fixtures/megger_frax/` and parametrise integration tests.

---

## 5. Phase 0 deliverables (DONE — this branch)

✅ Repo scaffold (`src/`, `tests/`, `standards/`, `docs/`, `frontend/`)
✅ `pyproject.toml` (uv) + Makefile + pre-commit + scripts
✅ `standards/ieee_c57_149_combinations.yaml` — 4 transformer types, 48 combinations, validator green
✅ `external/SFRA` cloned + this REFACTOR_MAP
✅ Design system handoff copied to `docs/design/` + `frontend/src/styles/design-tokens.css`
✅ `sfra_analysis/` core: bands, result_types, statistical, resample, verdict, transfer, standalone (Mode 2), compare (Mode 1), runner (Mode 1/2 dispatch)
✅ `sfra_analysis/io/`: base, combination_resolver, frax (real + legacy), csv, dispatch
✅ `cli.py` — `sfra-full analyse` (Mode 1/Mode 2), `frax-info`, `validate-catalogue`
✅ Test suite — 44 tests passing, 75% coverage on `sfra_full/sfra_analysis/*`
✅ End-to-end: parses `external/SFRA/backend/samples/{ref,test}.frax`, runs Mode 1 + Mode 2 with real numbers
