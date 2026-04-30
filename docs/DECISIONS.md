# DECISIONS — engineering choices that diverge from default expectations

Spec v2 §13 instruction: when standards conflict or the spec is ambiguous,
pick the stricter interpretation, log the decision here, cite the clause.
Keep entries chronological; never edit history.

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

## 2026-04-25 · Pole-fit algorithm
**Choice**: `transfer.fit_poles` uses `scipy.signal.invfreqs` per spec v2
§7.4 step 3, with order auto-search across (6, 8, 10). Upstream uses a
hand-rolled Sanathanan-Koerner LSTSQ iteration. Spec v1 originally called
for Gustavsen vector-fitting (`skrf.vectorFitting`) — we don't depend on
scikit-rf in Phase 0 because invfreqs is sufficient and lighter.
**Open**: if pole accuracy turns out to matter for verdict-level decisions
(currently advisory only), revisit and add scikit-rf.
