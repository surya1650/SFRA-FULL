# SFRA-FULL — APTRANSCO SFRA Diagnostic Tool

**Sweep Frequency Response Analysis** platform for power-transformer winding-condition assessment, conforming to **IEEE C57.149-2012**, **IEC 60076-18**, **DL/T 911-2004**, and **CIGRE TB 342 / TB 812**.

Built for APTRANSCO HIS (Transmission Corporation of Andhra Pradesh, High-voltage Substation Information System) field engineers. Ingests SFRA traces from MEGGER FRAX, OMICRON FRAnalyzer, Doble M5x00, and generic CSV/IEC/IEEE/CIGRE exports; produces per-band statistical indicators, resonance-shift diagnostics, severity verdicts, and APTRANSCO-letterhead PDF / XLSX reports.

---

## 1 · What you get

- **84 IEEE C57.149 combinations** seeded across four transformer types (TWO_WINDING=15, AUTO_WITH_TERTIARY_BROUGHT_OUT=21, AUTO_WITH_TERTIARY_BURIED=12, THREE_WINDING=36).
- **Mode 1** comparative analysis (reference + tested) — uncentered CC, ASLE, CSD, MM, MaxDev, DL/T 911 RL factor per band, resonance pairing with `matched/lost/new` classification, advisory pole fit, deterministic verdict + auto-remarks.
- **Mode 2** standalone analysis (single tested trace, no reference) — band-energy distribution, resonance density, peak irregularity, noise/SNR, abnormal-damping flags. Mode 1 supersedes Mode 2 automatically when a reference is uploaded later.
- **30+ REST endpoints** across health, standards, transformers, cycles, sessions, uploads (single + batch FRAX in one route), analyses (incl. reviewer sign-off), traces, reports, auth, audit.
- **PDF + XLSX reports** with per-combination plots, summary table, and `DRAFT — INCOMPLETE` watermark on partial sets.
- **Tamper-evident audit log** — every login / upload / analysis / threshold change / review hashes the previous row, with `GET /api/audit/verify` to detect any tampering.
- **Engineer / Reviewer / Admin** roles via JWT; admin-only threshold hot-reload, user creation, and chain verification.
- **React + TypeScript + Tailwind + Plotly** frontend with a 7-tab navigation matching the Claude Design system handoff (`docs/design/`), including a full **4-panel comparison view** per spec v2 §8.

---

## 2 · Quickstart — `docker compose up` (recommended)

Easiest path for substation laptops. Brings up Postgres 15 + FastAPI backend + nginx-fronted React build in one command.

### 2.1 Prereqs

- Docker 20.10+ and the `docker compose` v2 plugin.
- ~2 GB of free disk; ~1 GB RAM.

### 2.2 Steps

```bash
git clone https://github.com/surya1650/SFRA-FULL.git
cd SFRA-FULL

# 1. Generate the JWT signing secret + Postgres password.
cp .env.example .env
sed -i "s/replace-me-with-32-bytes-of-random-hex/$(openssl rand -hex 32)/" .env
sed -i "s/replace-me-postgres-pwd/$(openssl rand -hex 16)/" .env

# 2. Boot the stack.
docker compose up -d --build

# 3. Wait ~90 seconds for migrations + catalogue seed.
docker compose logs -f backend | head -40
# Look for "[entrypoint] Starting service: uvicorn ..."

# 4. Create the first admin user (one-time).
docker compose exec backend python3 -c "
from sfra_full.db import build_engine, build_sessionmaker
from sfra_full.auth import User, Role, hash_password
eng = build_engine()
Sm = build_sessionmaker(eng)
s = Sm()
s.add(User(email='admin@aptransco.gov.in', full_name='HIS Admin',
           hashed_password=hash_password('CHANGE_ME_ON_FIRST_LOGIN'),
           role=Role.ADMIN))
s.commit()
print('admin@aptransco.gov.in / CHANGE_ME_ON_FIRST_LOGIN')
"
```

### 2.3 Open in your browser

| URL | What it shows |
|---|---|
| **<http://localhost>** | The React UI — Dashboard / Upload & Configure / Traces / **Comparison & Indices (4-panel view)** / Failure Diagnosis / Modeling / Report tabs |
| <http://localhost:8000/api/health> | Backend liveness probe |
| <http://localhost:8000/docs> | Interactive OpenAPI / Swagger UI for every endpoint |

### 2.4 First user flow

1. Open <http://localhost>.
2. Use the **Upload & Configure** tab to register a transformer, open a commissioning cycle, and start a session.
3. Drop a `.frax` / `.csv` / `.fra` / `.xfra` file in the dropzone.
4. Click **Run analysis** — Mode 1 (with reference) or Mode 2 (without).
5. Switch to **Comparison & Indices** to see the **4-panel view**: tested magnitude, reference magnitude, tested phase, Δ-plot with ±3 dB watch and ±6 dB alarm lines, plus per-band metrics and the auto-generated remark.
6. Hit **Download PDF** in the Report tab when the session is complete.

---

## 3 · Quickstart — local dev (no Docker)

For developers who want to iterate on the analysis core or frontend.

### 3.1 Backend

```bash
git clone https://github.com/surya1650/SFRA-FULL.git
cd SFRA-FULL

# Optional: pull the upstream surya1650/SFRA repo for sample fixtures.
bash scripts/setup_external.sh

# Python 3.11+ required. uv is recommended (https://github.com/astral-sh/uv).
pip install uv
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Allow the dev JWT secret (don't ship this to prod).
export ALLOW_DEV_JWT_SECRET=1

# Initialise SQLite + seed the 84 combinations.
alembic upgrade head
python3 scripts/seed_combinations.py

# Run the FastAPI dev server.
uvicorn sfra_full.api.app:app --reload --port 8000
```

API now live on <http://localhost:8000>.

### 3.2 Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
# Vite dev server: http://localhost:5173, proxying /api → :8000
```

Open <http://localhost:5173> for hot-reload development. For production builds, `npm run build` emits a static bundle in `frontend/dist/`.

### 3.3 One-liner end-to-end demo

After steps 3.1 + 3.2 are running, with the upstream sample fixtures cloned:

```bash
# Create a demo admin (only once; idempotent if you skip if it errors).
PYTHONPATH=src python3 -c "
from sfra_full.db import build_engine, build_sessionmaker
from sfra_full.auth import User, Role, hash_password
eng = build_engine(); s = build_sessionmaker(eng)()
s.add(User(email='admin@aptransco.test', full_name='Demo Admin',
           hashed_password=hash_password('admin1234'), role=Role.ADMIN))
s.commit()
"

# Run the end-to-end demo (login → register → upload ref+test → analyse → PDF/XLSX).
ADMIN_EMAIL=admin@aptransco.test ADMIN_PASSWORD=admin1234 \
    bash scripts/demo.sh
```

The script walks login → register → cycle → session → upload ref + tested → analyse → audit-chain verify → download PDF + XLSX. It prints the verdict for each combination and saves the reports to `/tmp/sfra-demo.{pdf,xlsx}`.

---

## 4 · Repository layout

```
SFRA-FULL/
├── alembic/                       # SQLAlchemy migrations (initial + user + audit + chain)
├── docs/
│   ├── DECISIONS.md               # Engineering choices that diverge from defaults
│   ├── OPERATIONS.md              # 11-section ops runbook (deploy/backup/audit)
│   └── design/                    # Claude Design handoff bundle (verbatim)
├── frontend/                      # Vite + React + TypeScript + Tailwind
│   ├── src/api/                   # Typed API client + TanStack Query hooks
│   ├── src/components/            # Header, TabNav, Card, VerdictBadge, SfraPlot, DiffPlot
│   ├── src/tabs/                  # Dashboard / Upload / Traces / Comparison / Diagnosis / Modeling / Report
│   ├── Dockerfile / nginx.conf    # Two-stage Vite-build → nginx
│   └── tailwind.config.cjs        # Aligned with docs/design/ tokens
├── scripts/
│   ├── seed_combinations.py       # YAML → DB upsert of the 84 combinations
│   ├── validate_catalogue.py      # Catalogue schema + count enforcer (pre-commit hook)
│   ├── setup_external.sh          # Clone surya1650/SFRA into external/ for fixtures
│   ├── docker-entrypoint.sh       # Container bootstrap (migrations + seed + uvicorn)
│   └── demo.sh                    # End-to-end demo curl pipeline
├── src/sfra_full/
│   ├── api/                       # FastAPI app + 10 route modules
│   ├── audit/                     # AuditEvent ORM + tamper-evident hash chain + verifier
│   ├── auth/                      # JWT, bcrypt, role gates, SSO placeholder router
│   ├── db/                        # SQLAlchemy 2.x typed models + array helpers
│   ├── reports/                   # ReportLab PDF + openpyxl XLSX generators
│   ├── sfra_analysis/             # Pure analysis core
│   │   ├── bands.py               # YAML-loaded BandSpec + overlap helpers
│   │   ├── resample.py            # PCHIP regrid + 80% overlap guard
│   │   ├── statistical.py         # CC / ASLE / CSD / MM / RL per spec v2 §7.3
│   │   ├── transfer.py            # Resonance detection + matching + pole fit
│   │   ├── verdict.py             # DL/T 911 RL → severity + auto-remarks
│   │   ├── compare.py             # Mode 1 orchestrator
│   │   ├── standalone.py          # Mode 2 orchestrator
│   │   ├── runner.py              # Mode 1/2 dispatcher
│   │   └── io/                    # FRAX (real + legacy), CSV, Doble, OMICRON, dispatch
│   ├── storage/                   # Filesystem blob store with SHA-256 keying
│   └── cli.py                     # `sfra-full analyse / serve / seed-db / ...`
├── standards/
│   └── ieee_c57_149_combinations.yaml   # Single source of truth for 84 combinations
├── tests/
│   ├── conftest.py                # synthetic_trace_factory fixture
│   ├── unit/                      # Catalogue / bands / statistical / resample / runner / standalone / io / OEM-parsers
│   └── integration/               # DB / storage / API / reports / auth / audit / thresholds
├── alembic.ini · pyproject.toml · Makefile · pre-commit · Dockerfile · docker-compose.yml
├── CHANGELOG.md · REFACTOR_MAP.md
└── README.md (this file)
```

---

## 5 · CLI reference

The `sfra-full` CLI is installed by `pip install -e .` and exposes:

| Command | What it does |
|---|---|
| `sfra-full version` | Print the engine version. |
| `sfra-full validate-catalogue` | Re-run the YAML schema + count enforcer. |
| `sfra-full seed-db` | Upsert the 84 combinations into the DB (uses `SFRA_DATABASE_URL`). |
| `sfra-full frax-info <path>` | List every sweep in a `.frax` file with its resolved combination code. |
| `sfra-full analyse <tested> [--reference <ref>] [--out <json>]` | Mode 1 (with `--reference`) or Mode 2 (without) — JSON dump of `AnalysisOutcome`. |
| `sfra-full serve [--host --port --reload]` | Run the FastAPI dev server under uvicorn. |

Examples:

```bash
# Mode 2 on a single trace (no reference yet).
sfra-full analyse external/SFRA/backend/samples/test.frax \
    --transformer-type TWO_WINDING --combination-code EEOC_HV_R

# Mode 1 with both traces.
sfra-full analyse external/SFRA/backend/samples/test.frax \
    --reference external/SFRA/backend/samples/ref.frax \
    --transformer-type TWO_WINDING --combination-code EEOC_HV_R \
    --out /tmp/result.json
```

---

## 6 · Key API endpoints

See <http://localhost:8000/docs> for the live OpenAPI schema with request/response shapes.

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/api/health` | — | Liveness probe |
| GET | `/api/standards/combinations?transformer_type=…` | — | List the 15/21/12/36 combinations for a type |
| GET | `/api/standards/bands` | — | Spec v2 + DL/T 911 band definitions |
| GET | `/api/standards/thresholds` | — | Active DL/T 911 RL thresholds |
| PATCH | `/api/standards/thresholds` | ADMIN | Hot-reload thresholds (deep-merge into YAML, invalidate cache, audit) |
| POST | `/api/auth/login` | — | Form-encoded username + password → JWT |
| GET | `/api/auth/me` | any | Current user |
| POST | `/api/users` / GET `/api/users` | ADMIN | User CRUD |
| POST/GET | `/api/transformers` (+ `/{id}`) | — / any | Transformer registry |
| POST/GET | `/api/transformers/{id}/cycles` | any | Open / list overhaul cycles (auto-closes prior open cycle) |
| POST | `/api/transformers/{id}/sessions` | any | Start a test session |
| GET | `/api/transformers/{id}/sessions` | — | All sessions for the transformer |
| GET | `/api/cycles/{id}/sessions` | — | Sessions inside one cycle |
| GET | `/api/sessions/{id}` / `/traces` | — | Session metadata + trace list |
| POST | `/api/sessions/{id}/upload` | any | **Single-trace OR batch FRAX in one route** (spec v2 §6.1) |
| POST | `/api/sessions/{id}/analyse` | ENGINEER | Run Mode 1/2 across every TESTED trace |
| GET | `/api/sessions/{id}/analyses` | — | List analyses for the session |
| GET | `/api/analyses/{id}` | — | One analysis result |
| POST | `/api/analyses/{id}/review` | REVIEWER | Sign-off (or reject) with reviewer remarks + audit |
| GET | `/api/sessions/{id}/report.pdf` | — | APTRANSCO-letterhead PDF (DRAFT watermark on partial sets) |
| GET | `/api/sessions/{id}/report.xlsx` | — | Workbook with summary + per-combo + metadata sheets |
| GET | `/api/traces/{id}` / `/data` | — | Trace metadata or decoded numpy arrays |
| GET | `/api/audit` | REVIEWER | Filterable audit log (actor / action / target / before) |
| GET | `/api/audit/verify` | ADMIN | Verify the tamper-evident hash chain |

---

## 7 · Running the test suite

```bash
# Backend (90+ tests across catalogue / bands / statistical / resample /
# runner / standalone / io / OEM-parsers / db / storage / api / reports /
# auth / audit_thresholds):
PYTHONPATH=src pytest tests/

# Catalogue + schema validator:
python3 scripts/validate_catalogue.py

# Frontend:
cd frontend && npm run test
```

Coverage budget: **≥80 % on `src/sfra_full/sfra_analysis/*`**, currently 80 % across the entire `src/sfra_full/*` tree.

---

## 8 · Operations + day-2 maintenance

See **[`docs/OPERATIONS.md`](docs/OPERATIONS.md)** — 11 sections covering deployment topologies (substation / central / air-gapped), backups (Postgres + storage), threshold tuning, audit log, tap-position discipline, single-trace re-parse, engine upgrades, common issues.

For engineering choices that diverged from the defaults, see **[`docs/DECISIONS.md`](docs/DECISIONS.md)** (e.g. uncentered-CC vs Pearson, default 36-row THREE_WINDING set, hot-reload rewrites the YAML, audit hash chain).

---

## 9 · Standards traceability

| Spec | Where it lives |
|---|---|
| **IEEE C57.149-2012 Clause 5 + Table 1** (combination matrix) | `standards/ieee_c57_149_combinations.yaml` |
| **IEC 60076-18:2012** (band definitions) | YAML `bands.spec_v2` |
| **DL/T 911-2004** (RL factor + thresholds) | YAML `bands.dl_t_911` + `dl_t_911_thresholds`, applied by `sfra_analysis/verdict.py` |
| **CIGRE TB 342 / TB 812** (sub-band interpretation, severity ladder) | `sfra_analysis/verdict.py` auto-remarks templates |

The validator (`scripts/validate_catalogue.py`) blocks any commit that breaks the row counts or code patterns — guarantees the spec contract holds across UI / backend / reports / tests in one stroke.

---

## 10 · License + attribution

Built on top of [`surya1650/SFRA`](https://github.com/surya1650/SFRA) — the upstream is cloned into `external/SFRA/` (gitignored) by `scripts/setup_external.sh` and inventoried in `REFACTOR_MAP.md` (keep / wrap / rewrite / new). Spec v2 is the authoritative requirements document.

Internal use, APTRANSCO HIS division.
