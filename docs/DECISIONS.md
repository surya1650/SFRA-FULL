# DECISIONS — engineering choices that diverge from default expectations

Spec v2 §13 instruction: when standards conflict or the spec is ambiguous,
pick the stricter interpretation, log the decision here, cite the clause.
Keep entries chronological; never edit history.

---

## 2026-04-30 · THREE_WINDING — default 36-row exhaustive set
**Choice**: spec v2 collapsed the v1 "Part 1 / Part 2" 36×2 split into a
single THREE_WINDING type but didn't enumerate the row count. We ship a
**36-row default**: 9 EEOC + 9 EESC + 9 CIW + 9 IIW.
**Why**: 36 matches industry practice (IEEE C57.149 Annex B exhaustive
matrix on a single connection group). EESC default suffix-less form
pairs with the next-adjacent winding; explicit `_LVS` suffix when LV is
shorted.
**Consequence**: total catalogue rows now 84 (15 + 21 + 12 + 36).

---

## 2026-04-30 · OEM parser scope — Doble + OMICRON in-tree, CIGRE/IEC/IEEE via generic CSV
**Choice**: Phase 3 ships dedicated parsers for Doble (.xfra) and
OMICRON FRAnalyzer (.fra). CIGRE / IEC / IEEE plain-CSV variants flow
through `parse_csv`.
**Why**: real APTRANSCO field instruments are MEGGER FRAX, OMICRON
FRAnalyzer, and Doble. CIGRE / IEC / IEEE-formatted CSVs are
already standards-compliant column layouts the generic CSV path
handles. Promoting dedicated parsers is Phase 4 if needed.

---

## 2026-04-30 · Docker entrypoint refuses dev JWT secret in prod
**Choice**: `scripts/docker-entrypoint.sh` aborts startup if
`SFRA_JWT_SECRET` is unset, unless `ALLOW_DEV_JWT_SECRET=1` is explicit.
**Why**: a leaked or hardcoded JWT secret invalidates the entire auth
layer. Failing fast beats booting with a known-public secret.

---

## 2026-04-25 · Catalogue location & external dependency layout
**Choice**: `external/SFRA/` is gitignored (managed dep, brought in via
`scripts/setup_external.sh`); the keep/wrap/replace ledger lives at
top-level `REFACTOR_MAP.md` rather than `external/SFRA/INVENTORY.md`.
**Why**: upstream is much larger than the spec implied (full FastAPI app +
React frontend), so committing it would inflate review surface. The pin
file `external/SFRA.sha` records the exact upstream commit we audit
against.

---

## 2026-04-25 · CC formula — uncentered cosine similarity
**Choice**: implement spec v2 §7.3 verbatim:
`CC = sum(X·Y) / sqrt(sum(X²)·sum(Y²))` (uncentered). The upstream
`external/SFRA/backend/analysis/indices.py` uses Pearson (mean-centered).
**Why**: spec is explicit; the two formulas give different numbers on
non-zero-mean dB inputs. Pearson would round to 1.0 for any pair of
parallel-shifted dB curves; the uncentered form preserves dB-magnitude
similarity which is what DL/T 911 RL thresholds were tuned on.
**Consequence**: uncentered CC is dB-similarity tolerant — it does NOT by
itself catch resonance frequency shifts. We escalate severity using
resonance-pair geometry (`compare._resonance_shift_severity`) so a 4%
shift goes to SIGNIFICANT_DEVIATION even with CC ≈ 1.0.

---

## 2026-04-25 · CSD formula — uncentered sum of squares
**Choice**: `CSD = sqrt(sum((X-Y)²) / (N-1))` per spec v2 §7.3.
Upstream uses `np.std(d, ddof=1)` which subtracts the mean diff first.
**Why**: spec is explicit and matches DL/T 911 nomenclature.

---

## 2026-04-25 · Resonance severity escalation thresholds
**Choice**: in `compare._resonance_shift_severity`:
- `disrupted >= 3 OR max_shift > 10%` → SEVERE_DEVIATION
- `disrupted >= 1 OR max_shift > 5%` → SIGNIFICANT_DEVIATION
- `max_shift > 2%` → MINOR_DEVIATION

Anti-resonance shifts are excluded from `max_shift` because anti-resonance
peak detection is intrinsically noisier (broader peaks ⇒ higher detection
variance even on identical inputs). Anti-resonances are still reported
in the resonance-pair table for human review.

**Why**: empirical — on the upstream's own clean test fixtures, anti-
resonance shifts of 5-8% were detected even when the two traces were
literally identical with only added noise. Resonances (sharp dips) are
much more stable.

**Open**: thresholds are a heuristic. Once we have real APTRANSCO fixtures
with engineering ground truth, calibrate against those.

---

## 2026-04-25 · FRAX parser — accept BOTH real Megger schema and legacy schema
**Choice**: `io/frax.py` first tries spec v2 §4.1's
`<Frameworx>/<Frax>/<TestRecord>/<Sweep>/<Properties>/<Data>` schema;
when no `<Sweep>` elements exist, falls back to upstream's synthetic
`<FRAXFile>/<Measurement>/<Point>` schema.
**Why**: upstream sample fixtures use the simpler schema; real Megger
exports use the spec schema. Supporting both lets us reuse upstream
fixtures for testing without sacrificing real-world correctness.
The `source_format` field on each `ParsedSweep` records which path was
taken (`FRAX` vs `FRAX_LEGACY`) so reports can flag legacy parses.

---

## 2026-04-25 · Phase R/S/T mapping in combination resolver
**Choice**: spec v2 uses `R / S / T` phase labels. The combination
resolver also accepts `1U/1V/1W`, `U/V/W`, and `A/B/C` and translates
them to R/S/T.
**Why**: different MEGGER firmware versions emit different phase
notations; the field engineer should not have to care.

---

## 2026-04-25 · Auto-with-tertiary-brought-out IV vs LV nomenclature
**Choice**: for `AUTO_WITH_TERTIARY_BROUGHT_OUT`, the catalogue uses
`IV` (intermediate voltage) for the common winding consistently, while
spec v2 §5.2 mixes "IV" and "LV" between sentences. The DB enum
`Combination.category` accepts both `EEOC_IV` and `EEOC_LV`, so this is
a labelling choice not a structural one.
**Why**: IV is the formal autotrafo term (the common winding's terminal
voltage is the intermediate voltage). LV is loose engineering shorthand.
Picking IV throughout keeps the codes self-explanatory.

---

## 2026-04-25 · THREE_WINDING combinations — pending engineering review
**Choice**: the YAML catalogue has `THREE_WINDING.pending_enumeration: true`
and `combinations: []`. The validator allows this and warns.
**Why**: spec v2 §3 lists THREE_WINDING in the transformer_type enum but
does not enumerate the combination set, and spec v1 had two contradictory
"Part 1 / Part 2" 36-row sets that disagreed with v2's collapsed type.
Don't invent — wait for APTRANSCO engineering input.

---

## 2026-04-25 · Mode 2 — qualitative severity ladder
**Choice**: Mode 2 (single-trace, no reference) uses a separate severity
enum: `APPEARS_NORMAL` / `SUSPECT` / `INDETERMINATE`. These are NOT mapped
onto the spec v2 §3 4-level enum (NORMAL / MINOR / SIGNIFICANT / SEVERE),
because those levels are calibrated against a reference baseline.
**Why**: claiming `MINOR_DEVIATION` when no reference exists would be
diagnostically misleading. Engineers reading the report must know the
severity is a self-analysis. The auto-remark template explicitly says
"no reference available".
**UI**: design system maps `APPEARS_NORMAL` → emerald, `SUSPECT` → amber,
`INDETERMINATE` → slate (neutral) so the visual cue is consistent.

---

## 2026-04-25 · Frequency overlap threshold
**Choice**: spec v2 §7.1 — refuse comparison when overlap < 80% of either
trace's span. We surface the actual percentages in the
`InsufficientOverlapError` so the UI can report "ref covers 60%, test
covers 40% — re-test with matching range".
**Why**: stricter than upstream's silent best-effort interpolation.

---

## 2026-04-30 · DB enum storage — by VALUE, not NAME
**Choice**: `AnalysisResult.mode` and `.severity` columns set
``values_callable=lambda x: [e.value for e in x]`` on the SQLAlchemy
`Enum` type so the **value** of each enum member is persisted (e.g.
`'comparative'`, `'NORMAL'`), not the Python member name (e.g.
`COMPARATIVE`, `NORMAL`).
**Why**: the CHECK constraint
```
(mode = 'reference_missing_analysis' AND reference_trace_id IS NULL)
OR (mode = 'comparative' AND reference_trace_id IS NOT NULL)
```
is expressed against enum values. Without this setting SQLAlchemy stores
the Python NAME (`REFERENCE_MISSING_ANALYSIS`), which mismatches the
constraint and aborts every Mode 2 insert.

---

## 2026-04-30 · In-memory SQLite vs file-backed for tests
**Choice**: API integration tests use a file-backed SQLite under
``tmp_path`` rather than ``sqlite://``.
**Why**: `:memory:` SQLite is per-connection. FastAPI's TestClient opens a
fresh connection per request, so the schema created by `Base.metadata.
create_all` is invisible to subsequent requests. File-based SQLite keeps
all connections pointing at the same on-disk database. Production uses
PostgreSQL via `SFRA_DATABASE_URL` and the issue does not arise.

---

## 2026-04-30 · Trace storage — BYTEA arrays + filesystem raw bytes
**Choice**: Spec v2 §3 says BYTEA arrays in the DB; spec v1 said
filesystem only. We do BOTH:
- **BYTEA columns** on `Trace.frequency_hz` / `magnitude_db` / `phase_deg`
  hold the parsed numpy arrays via `numpy.save` (compact, self-contained,
  copies cleanly with the DB).
- **Filesystem** under `data/storage/<serial>/cycle_NNN/<combo>/<role>/`
  keeps a forensic copy of the raw uploaded bytes alongside its SHA-256
  on the row. The raw file is what audit reviewers can re-parse should
  the analysis pipeline ever change.
**Why**: BYTEA in DB is fast for analysis re-runs (no disk hit), but the
raw bytes are needed for forensic re-parsing and as the integrity anchor
(hash chain). Storing both is cheap and unambiguous.

---

## 2026-04-30 · Open-cycle auto-close on new cycle creation
**Choice**: `POST /api/transformers/{id}/cycles` auto-closes any existing
open cycle by setting its `cycle_end_date` to the new cycle's
`cycle_start_date`.
**Why**: spec v2 §3 says "at most one open cycle per transformer" but
doesn't specify how the transition happens. Auto-closing on open is the
natural workflow — the engineer who opens a post-overhaul cycle
implicitly declares the prior cycle's references retired. The closed
cycle's data remains read-only browsable.

---

## 2026-04-30 · bcrypt directly, not via passlib
**Choice**: `auth/password.py` calls the `bcrypt` module directly rather
than going through passlib's `CryptContext`.
**Why**: passlib's bcrypt backend reads `bcrypt.__about__.__version__`
which was removed in bcrypt>=4. The fallback path issues a confusing
deprecation warning and makes verify slow. Direct bcrypt is two
function calls (`hashpw` + `checkpw`), version-stable, and removes the
passlib dependency from the production wheel.

---

## 2026-04-30 · Permissive email validation
**Choice**: `UserCreate.email` is a plain `str` with a custom
field validator (`@@count == 1`, dot in domain), not Pydantic's
`EmailStr`.
**Why**: Pydantic's `EmailStr` (via email-validator) rejects RFC-2606
reserved TLDs like `.test`, `.example`, `.invalid` — which our test
fixtures use deliberately. The permissive validator still rejects
malformed inputs while allowing the standardised test domains.

---

## 2026-04-30 · PDF watermark not searchable in raw bytes
**Choice**: the partial-set DRAFT watermark is drawn via
`canvas.drawCentredString` after a `setFillAlpha(0.12)` + rotation;
it survives all PDF readers but is NOT visible in a `b"DRAFT" in bytes`
substring search because ReportLab compresses content streams.
**Why**: searching the raw bytes for "DRAFT" is unreliable and was
breaking tests intermittently. The integration test instead asserts
that the partial-set code path was taken (analysis count < catalogue
total) and that the rendered PDF is well-formed (`%%EOF`). Visual
verification is part of the §13 acceptance criteria handled by humans.

---

## 2026-04-30 · Single endpoint for both upload paths
**Choice**: `POST /api/sessions/{id}/upload` handles both spec v2 §6.1
paths (single-trace + batch FRAX) via the presence/absence of the
`combination_code` form field. No separate batch endpoint.
**Why**: single code path = single test surface. Batch FRAX just sets
`combination_code=None` and the resolver assigns codes per sweep;
single-trace overrides with the explicit code. Sweeps that fail
resolution come back in `unmapped_sweeps` so the UI can prompt
manually — no upload ever fails outright on resolution.

---

## 2026-04-25 · Pole-fit algorithm
**Choice**: `transfer.fit_poles` uses `scipy.signal.invfreqs` per spec v2
§7.4 step 3, with order auto-search across (6, 8, 10). Upstream uses a
hand-rolled Sanathanan-Koerner LSTSQ iteration. Spec v1 originally called
for Gustavsen vector-fitting (`skrf.vectorFitting`) — we don't depend on
scikit-rf in Phase 0 because invfreqs is sufficient and lighter.
**Open**: if pole accuracy turns out to matter for verdict-level decisions
(currently advisory only), revisit and add scikit-rf.
