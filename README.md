# SFRA-FULL — APTRANSCO SFRA Diagnostic Tool

<p>
  <img src="assets/branding/aptransco_logo.svg" alt="AP TRANSCO ISO 27001 - 2022" width="120" align="right">
</p>

**Sweep Frequency Response Analysis** platform for power-transformer winding-condition assessment — IEEE C57.149-2012 / IEC 60076-18 / DL/T 911-2004 / CIGRE TB 342 + TB 812 compliant.

Built for APTRANSCO HIS (Transmission Corporation of Andhra Pradesh, High-voltage Substation Information System). Ingests SFRA traces from MEGGER FRAX, OMICRON FRAnalyzer, Doble M5x00, and generic CSV/IEC/IEEE/CIGRE exports; produces per-band statistical indicators, resonance-shift diagnostics, severity verdicts, APTRANSCO-letterhead PDF + XLSX reports, and a tamper-evident audit trail.

---

## TL;DR — open the app on your laptop

You need **two terminal windows** open at the same time. Terminal A runs the backend (Python + FastAPI on port 8000); Terminal B runs the frontend (Vite + React on port 5173). The frontend talks to the backend via a Vite proxy.

```
┌────────────────────────────────────┐    ┌────────────────────────────────────┐
│ Terminal A — backend               │    │ Terminal B — frontend              │
│                                    │    │                                    │
│ uvicorn on http://localhost:8000   │    │ vite on    http://localhost:5173   │
│   /api/health  /docs  …            │    │   proxies /api → :8000             │
│                                    │    │                                    │
└────────────────────────────────────┘    └────────────────────────────────────┘
```

Open **<http://localhost:5173>** in your browser when both are running. The Swagger docs live at **<http://localhost:8000/docs>**.

---

## 1 · One-time setup (do these once after cloning)

```bash
# Clone
git clone https://github.com/surya1650/SFRA-FULL.git
cd SFRA-FULL

# (Optional) pull the upstream surya1650/SFRA repo so demo fixtures exist.
bash scripts/setup_external.sh
```

### Backend prereqs

- **Python 3.11+** (`python3 --version` to check).
- A virtual env tool — either Python's built-in `venv` (always available) or `uv` (faster, recommended; `pip install uv`).

### Frontend prereqs

- **Node.js 18+** (`node --version` to check).
- `npm` (ships with Node).

---

## 2 · Run the backend in Terminal A

```bash
cd SFRA-FULL

# 2.1  Create + activate a virtual env (only the first time).
python3 -m venv .venv
source .venv/bin/activate     # on Windows PowerShell: .venv\Scripts\Activate.ps1

# 2.2  Install all Python deps in editable mode.
pip install --upgrade pip
pip install -e ".[dev]"

# 2.3  Allow the backend to boot without setting a real JWT secret
#      (DEV ONLY — the entrypoint refuses to start in production
#      without SFRA_JWT_SECRET).
export ALLOW_DEV_JWT_SECRET=1

# 2.4  Initialise the SQLite DB at ./data/app.db and seed the 84 combinations.
alembic upgrade head
python3 scripts/seed_combinations.py

# 2.5  Start the FastAPI dev server with auto-reload.
uvicorn sfra_full.api.app:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

Quick smoke check (in another shell or browser):
- <http://localhost:8000/api/health> → `{"status":"ok","version":"…"}`
- <http://localhost:8000/docs> → interactive Swagger UI for **30+ endpoints**

**Leave Terminal A running.**

---

## 3 · Run the frontend in Terminal B

Open a **new** terminal (don't close Terminal A).

```bash
cd SFRA-FULL/frontend

# 3.1  Install JS deps (only the first time, takes ~30 s).
npm install

# 3.2  Start the Vite dev server.
npm run dev
```

You should see:
```
  VITE v5.4.x  ready in xxx ms
  ➜  Local:   http://localhost:5173/
```

Open <http://localhost:5173> in your browser. The 7-tab navigation is live: **Dashboard · Upload & Configure · Traces & Graphs · Comparison & Indices · Failure Diagnosis · Modeling · Report**.

**Leave Terminal B running.** Hot-reload is on — edits to `frontend/src/**` refresh in the browser instantly.

---

## 4 · Click-through demo (5 minutes)

With both terminals running:

1. Open <http://localhost:5173>.
2. Go to **Upload & Configure** (tab 2).
3. Click **Create + open cycle + start session** (defaults are fine for a demo).
4. **Drag-and-drop a sample SFRA file** into the dropzone:
   - If you ran `scripts/setup_external.sh`, you have:
     - `external/SFRA/backend/samples/ref.frax` → upload as **REFERENCE**, combination `EEOC_HV_R`
     - `external/SFRA/backend/samples/test.frax` → upload as **TESTED**, combination `EEOC_HV_R`
   - Otherwise, any `.frax` / `.csv` / `.fra` / `.xfra` you have on disk works.
5. Click **Run analysis (Mode 1/2)**. The Phase 0 + Phase 1 pipelines fire — you should see one row per uploaded TESTED trace with a severity badge and an auto-remark.
6. Switch to **Comparison & Indices** (tab 4).
7. Pick the same transformer + session + analysis row. The **4-panel view** lights up:
   - tested magnitude (top-left)
   - reference magnitude (top-right)
   - tested phase (bottom-left)
   - **Δ-plot** with ±3 dB watch + ±6 dB alarm dashed lines (bottom-right)
8. Below the plots: **per-band metrics table** + auto-remark + session traces table.

---

## 5 · End-to-end shell demo (no browser needed)

The repo ships a `curl`-based smoke pipeline that hits every important endpoint:

```bash
# Create a demo admin user (in Terminal A's venv).
PYTHONPATH=src python3 -c "
from sfra_full.db import build_engine, build_sessionmaker
from sfra_full.auth import User, Role, hash_password
eng = build_engine(); s = build_sessionmaker(eng)()
s.add(User(email='admin@aptransco.test', full_name='Demo Admin',
           hashed_password=hash_password('admin1234'), role=Role.ADMIN))
s.commit()
"

# Run the demo (Terminal A still running).
ADMIN_EMAIL=admin@aptransco.test ADMIN_PASSWORD=admin1234 \
    bash scripts/demo.sh
```

The script logs in → registers a transformer → opens a commissioning cycle → starts a routine session → uploads `ref.frax` + `test.frax` → runs analysis → verifies the audit hash chain → downloads PDF + XLSX reports to `/tmp/sfra-demo.{pdf,xlsx}`.

---

## 6 · Stopping + restarting

- Stop the backend (Terminal A): `Ctrl+C`.
- Stop the frontend (Terminal B): `Ctrl+C`.
- Restart later: just run **steps 2.5** (uvicorn) and **3.2** (`npm run dev`) again — the venv, deps, and DB are persistent.
- Wipe everything and start clean: `rm -rf data/app.db data/storage` then re-run `alembic upgrade head` + `python3 scripts/seed_combinations.py`.

---

## 7 · Production-style deployment with Docker (one-shot)

If you don't want to run two terminals and just want everything live:

```bash
cp .env.example .env
sed -i "s/replace-me-with-32-bytes-of-random-hex/$(openssl rand -hex 32)/" .env
sed -i "s/replace-me-postgres-pwd/$(openssl rand -hex 16)/" .env

docker compose up -d --build
# Wait ~90 s for migrations + seed.
```

Then:
- **<http://localhost>** — production React build behind nginx
- **<http://localhost:8000/docs>** — backend Swagger
- See `docs/OPERATIONS.md` for the full ops guide (backups, threshold tuning, audit, upgrades).

---

## 8 · What you get

| Capability | Where it lives |
|---|---|
| **84 IEEE C57.149 combinations** seeded across 4 transformer types (15 + 21 + 12 + 36) | `standards/ieee_c57_149_combinations.yaml` |
| **Mode 1** (reference + tested) — uncentered CC, ASLE, CSD, MM, MaxDev, DL/T 911 RL factor per band; resonance pairing with `matched/lost/new`; advisory pole fit | `src/sfra_full/sfra_analysis/{statistical,transfer,compare}.py` |
| **Mode 2** (single trace, no reference) — band energy, resonance density, peak irregularity, noise/SNR, abnormal-damping flags. Auto-superseded by Mode 1 when a reference is uploaded later. | `src/sfra_full/sfra_analysis/standalone.py` |
| **Parsers** — MEGGER FRAX (real + legacy), OMICRON FRAnalyzer, Doble M5x00, generic CSV/TSV with auto Hz/kHz + deg/rad detection | `src/sfra_full/sfra_analysis/io/` |
| **30+ REST endpoints** + interactive OpenAPI | `src/sfra_full/api/` |
| **PDF + XLSX reports** with APTRANSCO letterhead slot, per-combination plots, summary table, **DRAFT — INCOMPLETE watermark** on partial sets | `src/sfra_full/reports/` |
| **Tamper-evident audit log** — every action hashes the previous row; `GET /api/audit/verify` detects any UPDATE/DELETE/reorder | `src/sfra_full/audit/` |
| **JWT auth** — Engineer / Reviewer / Admin roles; admin-only threshold hot-reload, user creation, chain verification | `src/sfra_full/auth/` |
| **React + TypeScript + Tailwind + Plotly** frontend with 7-tab nav and 4-panel comparison view | `frontend/` |

---

## 9 · Key API endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Liveness probe |
| `GET` | `/api/standards/combinations?transformer_type=…` | 15/21/12/36 combinations for a type |
| `GET` `PATCH` | `/api/standards/thresholds` | Read / hot-reload DL/T 911 RL thresholds (admin) |
| `POST` | `/api/auth/login` | Form-encoded login → JWT |
| `POST` `GET` | `/api/transformers` | Transformer registry |
| `POST` `GET` | `/api/transformers/{id}/cycles` | Open / list overhaul cycles |
| `POST` `GET` | `/api/transformers/{id}/sessions` | Test sessions |
| `POST` | `/api/sessions/{id}/upload` | **Single-trace OR batch FRAX in one route** (spec v2 §6.1) |
| `POST` `GET` | `/api/sessions/{id}/analyse` / `/analyses` | Run + list Mode 1 / Mode 2 |
| `POST` | `/api/analyses/{id}/review` | Reviewer sign-off (REVIEWER+) |
| `GET` | `/api/sessions/{id}/report.pdf` / `.xlsx` | Reports |
| `GET` | `/api/traces/{id}/data` | Decoded numpy arrays for plotting |
| `GET` | `/api/audit` / `/api/audit/verify` | Audit log + tamper verification |

Full OpenAPI: <http://localhost:8000/docs> while the backend is running.

---

## 10 · Running the test suite

```bash
# In Terminal A's venv, with the backend NOT running (tests use their own in-memory DB):
PYTHONPATH=src pytest tests/

# Validate the catalogue YAML schema:
python3 scripts/validate_catalogue.py

# Frontend tests (Vitest):
cd frontend && npm run test
```

86 tests pass at 80 % coverage on `src/sfra_full/*`.

---

## 11 · Troubleshooting

| Symptom | Fix |
|---|---|
| `uvicorn: command not found` | `pip install -e ".[dev]"` inside the venv (step 2.2). |
| `npm install` errors on `node-gyp` | Make sure Node 18+ is installed; older Node ships a broken native-build chain. |
| Backend logs `SFRA_JWT_SECRET unset` | Run `export ALLOW_DEV_JWT_SECRET=1` in Terminal A before `uvicorn`. |
| Frontend shows `Failed to fetch /api/health` | Backend isn't running — go check Terminal A. |
| Browser shows CORS errors hitting `:5173` | The Vite proxy handles `/api/*` automatically. If you're hitting a non-`/api` URL, point your fetch at `http://localhost:8000` directly. |
| `Database is locked` (SQLite) | Stop the backend, delete `data/app.db`, re-run `alembic upgrade head` + the seeder. |
| Comparison tab says "Select a trace to plot" forever | Make sure you ran **Run analysis** in step 4.5; only analysed traces show up in the analysis-row dropdown. |
| Reports tab buttons disabled | The session needs at least one analysed combination — run analysis first. |

---

## 12 · Repository layout

```
SFRA-FULL/
├── alembic/                       # SQLAlchemy migrations (initial + user + audit + chain)
├── assets/branding/               # APTRANSCO logo SVG (committed) + README
├── docs/
│   ├── DECISIONS.md               # Engineering choices that diverge from defaults
│   ├── OPERATIONS.md              # 11-section ops runbook (deploy/backup/audit)
│   └── design/                    # Claude Design handoff bundle (verbatim)
├── frontend/                      # Vite + React + TypeScript + Tailwind
│   ├── src/api/                   # Typed API client + TanStack Query hooks
│   ├── src/components/            # Header, TabNav, Card, VerdictBadge, SfraPlot, DiffPlot
│   ├── src/tabs/                  # Dashboard / Upload / Traces / Comparison / Diagnosis / Modeling / Report
│   └── tailwind.config.cjs        # Aligned with docs/design/ tokens
├── scripts/
│   ├── seed_combinations.py       # YAML → DB upsert of the 84 combinations
│   ├── validate_catalogue.py      # Catalogue schema + count enforcer (pre-commit hook)
│   ├── setup_external.sh          # Clone surya1650/SFRA into external/ for demo fixtures
│   ├── docker-entrypoint.sh       # Container bootstrap (migrations + seed + uvicorn)
│   └── demo.sh                    # End-to-end demo curl pipeline
├── src/sfra_full/
│   ├── api/                       # FastAPI app + 9 route modules
│   ├── audit/                     # AuditEvent ORM + tamper-evident hash chain + verifier
│   ├── auth/                      # JWT, bcrypt, role gates
│   ├── db/                        # SQLAlchemy 2.x typed models + array helpers
│   ├── reports/                   # ReportLab PDF + openpyxl XLSX generators
│   ├── sfra_analysis/             # Pure analysis core
│   │   ├── bands · resample · statistical · transfer · verdict · compare · standalone · runner
│   │   └── io/                    # FRAX (real + legacy), CSV, Doble, OMICRON, dispatch
│   ├── storage/                   # Filesystem blob store with SHA-256 keying
│   └── cli.py                     # `sfra-full analyse / serve / seed-db / …`
├── standards/
│   └── ieee_c57_149_combinations.yaml   # Single source of truth for 84 combinations
├── tests/
│   ├── conftest.py                # synthetic_trace_factory fixture
│   ├── unit/                      # catalogue / bands / statistical / resample / runner / standalone / io / OEM-parsers
│   └── integration/               # DB / storage / API / reports / auth / audit / thresholds
├── alembic.ini · pyproject.toml · Makefile · pre-commit · Dockerfile · docker-compose.yml
├── CHANGELOG.md · REFACTOR_MAP.md · SFRA_FULL_Requirements.md
└── README.md (this file)
```

---

## 13 · Operations + decisions

- **`docs/OPERATIONS.md`** — 11 sections covering deployment topologies (substation laptop / central HIS / air-gapped), backups (Postgres + storage), threshold tuning, audit log, tap-position discipline, single-trace re-parse, engine upgrades, common operational issues.
- **`docs/DECISIONS.md`** — engineering choices that diverged from defaults (uncentered-CC vs Pearson, default 36-row THREE_WINDING set, hot-reload rewrites the YAML, audit hash-chain implementation notes, SSO router intentionally removed for now).

## 14 · Standards traceability

| Spec | Where it lives in code |
|---|---|
| **IEEE C57.149-2012 Clause 5 + Table 1** (combination matrix) | `standards/ieee_c57_149_combinations.yaml` |
| **IEC 60076-18:2012** (band definitions) | YAML `bands.spec_v2` |
| **DL/T 911-2004** (RL factor + thresholds) | YAML `bands.dl_t_911` + `dl_t_911_thresholds`, applied by `sfra_analysis/verdict.py` |
| **CIGRE TB 342 / TB 812** (sub-band interpretation, severity ladder) | `sfra_analysis/verdict.py` auto-remarks templates |

The validator (`scripts/validate_catalogue.py`) blocks any commit that breaks the row counts or code patterns — guarantees the spec contract holds across UI / backend / reports / tests in one stroke.

---

Internal use, APTRANSCO HIS division.
Built on top of [`surya1650/SFRA`](https://github.com/surya1650/SFRA) — see [`REFACTOR_MAP.md`](REFACTOR_MAP.md) for the keep / wrap / rewrite / new ledger.
