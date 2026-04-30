# SFRA Diagnostic Tool — Design System

## Product Overview

**SFRA Diagnostic Tool** is a full-stack web application for **Sweep Frequency Response Analysis (SFRA)** of power transformers. It parses all major SFRA file formats (Megger FRAX, Doble, Omicron, CIGRE, IEC, IEEE), computes every standard comparison index, and presents results in an interactive React UI with Plotly.js graphs, sub-band analysis, failure mode diagnosis, and PDF/CSV export.

### Sources

- **Codebase**: Local folder `sfra/` (FastAPI backend + React/Vite frontend)
  - Backend: `sfra/backend/` — FastAPI, Pydantic, SciPy analysis engine
  - Frontend: `sfra/frontend/src/` — React + Tailwind CSS + Plotly.js
  - `sfra/README.md` — full feature & API documentation
- **Thesis**: `uploads/sfra thesis.pdf` — "Frequency Response Analysis for Transformer Winding Condition Monitoring", Mohd Fairouz Bin Mohd Yousof, University of Queensland, 2015 (221pp). Academic foundation for FRA interpretation, Nyquist plots, pole-zero analysis.

---

## Products / Surfaces

| Surface | Path | Description |
|---|---|---|
| **Web App** | `sfra/frontend/src/` | Main diagnostic tool — upload, visualise, compare, report |
| **REST API** | `sfra/backend/main.py` | FastAPI endpoints for analysis |

---

## Content Fundamentals

**Tone**: Technical, precise, professional. Written for power-systems engineers and asset managers. No marketing language.

**Voice**: Second-person ("Pick a reference and a test trace"), imperative, direct.

**Casing**: Sentence case for labels and UI text. ALL CAPS used only for verdict badges (GOOD / MARGINAL / BAD). Title case for section headings.

**Numerics**: High-precision floating point (4–6 decimal places) in analysis tables. Scientific notation (e.g. `1.234e-5`) when values < 1e-3 or ≥ 1e4. Frequency in Hz, magnitude in dB, phase in degrees.

**Abbreviations**: Standard domain abbreviations are used freely: CC, SD, ASLE, CSD, ED, MM, SSRE, SSE, FRA, SFRA, CIGRE, IEC, IEEE.

**Emoji**: Used sparingly for mode toggles only (`☀ Light` / `🌙 Dark`, `✓`, `!`, `⚠`, `✖`). Not used decoratively.

**Placeholders**: "–" (en dash) for missing or null numerical values.

**Example copy**:
- "Sweep Frequency Response Analysis for power transformers · CIGRE TB 342 / IEC 60076-18 / IEEE C57.149"
- "Reference vs test numerical-indices assessment."
- "No classification available — run Analyze first."
- "Optional notes to include in the PDF report…"

---

## Visual Foundations

### Color System

Primary brand is **blue** (Tailwind blue scale):

| Token | Hex | Usage |
|---|---|---|
| `brand-50` | `#eff6ff` | Light backgrounds, tinted badges |
| `brand-500` | `#3b82f6` | Accent elements |
| `brand-600` | `#2563eb` | Primary buttons, active tabs, active borders |
| `brand-900` | `#1e3a8a` | Header gradient start, dark fills |

Neutral base is **Slate** (full Tailwind slate scale). Light mode: `slate-900` text on `white`/`slate-50` backgrounds. Dark mode: `slate-100` text on `slate-800`/`slate-900` backgrounds.

**Semantic / Verdict colors** (core to the product):

| Verdict | Light bg | Light text | Dark bg | Dark text |
|---|---|---|---|---|
| Good / Normal | `emerald-100` | `emerald-800` | `emerald-900/40` | `emerald-200` |
| Marginal / Slight | `amber-100` | `amber-800` | `amber-900/40` | `amber-200` |
| Moderate | `orange-100` | `orange-800` | `orange-900/40` | `orange-200` |
| Bad / Severe | `rose-100` | `rose-800` | `rose-900/40` | `rose-200` |
| Critical | `red-100` | `red-800` | `red-900/40` | `red-200` |
| Unknown | `slate-100` | `slate-700` | `slate-800` | `slate-200` |

**Severity gradient headers** (SeverityDashboard): full-bleed `bg-gradient-to-r` from darker to lighter shade of the severity color.

### Typography

**Font stack**: `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif` — no custom webfonts. Closest Google Fonts match: **Inter** (flagged as substitution — see Fonts section).

**Scale**:
- `text-2xl font-bold` — Page title (H1)
- `text-lg font-semibold` — Card/section headings (H2)
- `text-sm font-semibold` — Sub-headings, labels
- `text-sm` — Body, table content
- `text-xs` — Metadata, captions, frequency ranges
- `font-mono text-sm/xs` — All numerical data in tables

**Tracking**: `tracking-wide uppercase text-xs` for category/status labels.

### Spacing & Layout

- Max content width: `max-w-7xl` (1280px) centered with `px-6` padding
- Grid: `lg:grid-cols-2`, `md:grid-cols-2`, `grid-cols-4` — responsive CSS grid
- Card spacing: `p-5` standard, `p-3` compact, `gap-4`/`gap-6` between cards
- Section spacing: `space-y-4`, `space-y-6`

### Cards

`.card` = `bg-white dark:bg-slate-800 rounded-lg shadow border border-slate-200 dark:border-slate-700`

No colored left-border accent. Shadow is subtle (Tailwind `shadow`). Border radius: `rounded-lg` (~8px). No gradients inside cards except the SeverityDashboard header.

### Buttons

- **Primary**: `bg-brand-600 hover:bg-brand-500 text-white px-3 py-1.5 rounded text-sm`
- **Secondary/Neutral**: `bg-slate-700 hover:bg-slate-600 text-white px-3 py-1.5 rounded text-sm`
- **Toggle active**: `bg-brand-600 text-white`
- **Toggle inactive**: `bg-slate-200 dark:bg-slate-700`
- **Disabled**: `disabled:opacity-50` — no color change, just opacity

### Header

Full-width `bg-gradient-to-r from-brand-900 to-brand-600` header. White text on gradient. Subtitle line at `text-sm text-brand-50/80`.

### Navigation

Tab bar: `bg-white dark:bg-slate-800 border-b`. Active tab: `border-b-2 border-brand-600 text-brand-700`. Inactive: `border-transparent text-slate-600 hover:text-brand-600`. No filled backgrounds on tabs.

### Backgrounds

- Light mode: `white` body, `white` cards
- Dark mode: `slate-900` body, `slate-800` cards
- Header: gradient only. No page-level background gradients or textures.

### Animations / Transitions

Minimal. `transition-colors` on nav tabs and buttons. No bounces, no spring animations. No entrance animations. Loading states use text change ("Analyzing…") rather than spinners.

### Borders & Radius

- Cards: `rounded-lg` (8px), `border border-slate-200`
- Inputs/selects: `rounded border border-slate-300`
- Buttons: `rounded` (4px)
- Badges/verdicts: `rounded` or `rounded px-2`
- Circles (severity icon): `rounded-full`

### Shadows

Single level: Tailwind `shadow` (~0 1px 3px rgba(0,0,0,0.1)). No elevation system. No inner shadows.

### Dark Mode

Class-based (`darkMode: "class"` in Tailwind). Toggled via header button. Consistent use of `dark:` variants throughout. Background: `slate-900`. Cards: `slate-800`. Borders: `slate-700`. Text: `slate-100`/`slate-300`.

### Data Visualization

Plotly.js for interactive frequency response charts. Log-scale X axis. CIGRE sub-band shading overlay. Per-trace color picker. Dark mode aware.

---

## Iconography

**Approach**: No icon font or SVG icon library used. Icons are Unicode characters / emoji used inline in text:
- `☀` (sun) — light mode
- `🌙` (moon) — dark mode  
- `✓` — normal/good condition
- `!` — slight deviation
- `⚠` — moderate/severe warning
- `✖` — critical failure

No SVG illustration system. No decorative icons. Icon usage is functional only (status indication).

**Substitution note**: The codebase has no icon assets to copy. If icons are needed in derivative designs, use **Heroicons** (outline, 1.5px stroke) from CDN — they match the minimal, clean aesthetic.

---

## Fonts

**Current**: System font stack (`system-ui, -apple-system, "Segoe UI", Roboto`). No webfonts bundled.

**Substitution**: Google Fonts **Inter** is used in this design system as the nearest equivalent. ⚠️ *Flag: If you want custom branding, provide a webfont (woff2) to replace Inter.*

---

## File Index

```
README.md                    ← this file
colors_and_type.css          ← CSS custom properties for colors, type, spacing
assets/                      ← logos, icons, brand assets
preview/
  colors-brand.html          ← brand blue palette
  colors-neutral.html        ← slate neutral palette
  colors-semantic.html       ← verdict / severity semantic colors
  type-scale.html            ← typography scale specimens
  type-mono.html             ← monospace / data type styles
  spacing-tokens.html        ← spacing, radius, shadow tokens
  component-buttons.html     ← button states
  component-cards.html       ← card variants
  component-verdicts.html    ← verdict badges
  component-severity.html    ← severity dashboard header
  component-table.html       ← data table / index table
  component-tabs.html        ← navigation tabs
  component-inputs.html      ← form inputs
ui_kits/
  sfra/
    index.html               ← full SFRA app UI kit
    README.md
SKILL.md
```
