# OPERATIONS — APTRANSCO SFRA platform

Field deployment, day-2 maintenance, and audit guide for the substation
SFRA Diagnostic Tool. Audience: APTRANSCO HIS engineers and the on-site
operator running the laptop / VM.

---

## 1. Deployment topologies

### 1.1 Substation laptop (single-host, recommended for routine use)

```bash
git clone https://github.com/surya1650/SFRA-FULL.git
cd SFRA-FULL
echo "SFRA_JWT_SECRET=$(openssl rand -hex 32)" > .env
echo "POSTGRES_PASSWORD=$(openssl rand -hex 16)" >> .env
docker compose up -d
```

After ~2 minutes:
- Frontend: <http://localhost>
- API:      <http://localhost:8000>
- OpenAPI:  <http://localhost:8000/docs>

### 1.2 Central HIS server (multi-substation)

Same compose stack, but expose only the frontend through the bastion
nginx. Set `POSTGRES_PASSWORD`, `SFRA_JWT_SECRET`, and run
`docker compose up -d` behind an internal-network firewall rule. Mount
`storage` and `db_data` to a NAS-backed volume so backups can run
nightly without touching the container.

### 1.3 Air-gapped substation

Build images on a connected workstation, push to a USB-stick registry
or `docker save`/`docker load`, then deploy. The image carries every
runtime dependency — no internet at deploy time.

---

## 2. First-run checklist

| # | Action | How |
|---|---|---|
| 1 | Create the admin user | `docker compose exec backend python3 -c "from sfra_full.db import build_engine, build_sessionmaker; from sfra_full.auth import User, Role, hash_password; eng = build_engine(); Sm = build_sessionmaker(eng); s = Sm(); s.add(User(email='admin@aptransco.gov.in', full_name='HIS Admin', hashed_password=hash_password('CHANGE_ME'), role=Role.ADMIN)); s.commit()"` |
| 2 | Drop the APTRANSCO logo | Copy `aptransco_logo.png` into the `branding` volume: `docker cp aptransco_logo.png $(docker compose ps -q backend):/app/assets/branding/` |
| 3 | Verify health | `curl http://localhost:8000/api/health` → `{"status":"ok",...}` |
| 4 | Verify combinations seeded | `curl 'http://localhost:8000/api/standards/combinations?transformer_type=TWO_WINDING' \| jq '. \| length'` → `15` |
| 5 | Register a transformer | Use the **Upload & Configure** tab in the UI, or `POST /api/transformers`. |

---

## 3. Backups

### 3.1 Postgres

```bash
docker compose exec -T db pg_dump -U sfra sfra | gzip > backups/sfra-$(date +%F).sql.gz
```

Schedule via cron on the host. Retain 30 daily, 12 monthly.

### 3.2 Trace blobs

The `storage` volume holds raw uploaded files (SHA-256 keyed). They are
the integrity anchor — the parsed numpy arrays in the DB can always be
re-derived from these. Backup with rsync:

```bash
docker run --rm -v sfra-full_storage:/storage -v $(pwd)/backups:/dest \
    alpine sh -c "tar czf /dest/storage-$(date +%F).tar.gz -C /storage ."
```

### 3.3 Reports cache

`reports` is regenerable from the DB; back up only if you want to
preserve reviewer-signed PDFs verbatim.

---

## 4. Threshold tuning

DL/T 911 RL thresholds and band ranges live in
`standards/ieee_c57_149_combinations.yaml`. Edit, then:

```bash
docker compose exec backend python3 scripts/validate_catalogue.py
docker compose restart backend
```

The catalogue is hot-reloaded on the next analysis run. Existing
analyses are NOT recomputed automatically — re-run the analysis
endpoint per session if you need updated severities:

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
    http://localhost:8000/api/sessions/{id}/analyse
```

---

## 5. Audit log

All engineer actions (upload, overwrite, generation change, report
generation) write to `data/audit/audit-YYYY-MM-DD.log` on the backend
volume. Tail the file or rsync it off-host.

> Phase 4: structured audit table in Postgres + tamper-evident hash
> chain. Until then, treat the file as append-only.

---

## 6. Tap-position discipline

Spec v2 §6.1 mandates that every uploaded trace carries:
- `tap_position_current` — required.
- `tap_position_previous` — required if upload role = TESTED and the
  trace is the first after a tap change.
- `detc_tap_position` — required if the transformer has DETC.

The UI form blocks submission when these are missing. If you bypass the
UI (CLI / Postman), the form-data fields are required and the backend
rejects the upload with HTTP 422.

---

## 7. Hot-reload of thresholds without restart

For threshold-only edits (no schema change), use:

```bash
curl -X PATCH http://localhost:8000/api/standards/bands \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -d @new_thresholds.json
```

> Endpoint planned for Phase 4. Until then the YAML edit + container
> restart in §4 is the supported path.

---

## 8. Restoring a single trace

Each Trace row carries a `source_file_sha256` and a `source_file_path`
relative to the storage root. To re-parse a trace:

```bash
docker compose exec backend python3 -m sfra_full.cli analyse \
    /app/data/storage/<serial>/cycle_NNN/<combo>/<role>/<sha8>_<file> \
    --reference /app/data/storage/<serial>/cycle_NNN/<combo>/reference/<sha8>_<file>
```

The output is a JSON dump of the AnalysisOutcome that you can compare
against the stored `analysis_result.indicators_json`.

---

## 9. Upgrading the engine

```bash
git pull
docker compose build
docker compose up -d
```

Alembic migrations run automatically at container start. If a migration
fails, the container logs the error and exits non-zero — Postgres data
is untouched and a rollback is `git checkout <previous-tag> && docker compose up -d`.

Engine version is recorded on every `analysis_result.engine_version`
row, so old analyses remain attributed to the version that produced
them. Re-running `/analyse` regenerates the rows under the new engine
version.

---

## 10. Common operational issues

| Symptom | Cause | Fix |
|---|---|---|
| `SFRA_JWT_SECRET unset` at startup | `.env` missing or wrong path | `echo "SFRA_JWT_SECRET=$(openssl rand -hex 32)" >> .env` |
| Upload returns `500: Parse error` | Truncated or wrong-format file | Try `sfra-full frax-info <file>` to inspect |
| Mode 2 result keeps showing after reference upload | Reference uploaded into a different cycle | Confirm `overhaul_cycle_id` matches; the matcher only pairs within one cycle |
| PDF report missing letterhead | `aptransco_logo.png` not in branding volume | Copy via `docker cp` per §2 |
| Threshold change doesn't apply | Container not restarted | `docker compose restart backend` |
| `combination_code not in catalogue for this transformer type` warning | FRAX sweep maps to a code not seeded for this type | Either change the transformer type or add the row to the YAML and re-seed |

---

## 11. Phase 3 caveats

- **THREE_WINDING** carries the default 36-row enumeration. APTRANSCO
  engineering may prune to a 18- or 24-row subset; flag in
  `docs/DECISIONS.md` before changing the YAML.
- **OEM parsers** ship for FRAX, FRAX legacy, OMICRON, Doble, and
  generic CSV. CIGRE / IEC / IEEE plain-CSV variants flow through the
  generic CSV parser today; promoting them into dedicated parsers is
  Phase 4 work.
- **SSO** is wired as an APIRouter placeholder returning 501 until
  APTRANSCO IdP details are confirmed.
- **Audit log** is filesystem-only today; structured table coming in
  Phase 4.
