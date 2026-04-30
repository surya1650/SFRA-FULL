# SFRA Diagnostic Tool — Frontend

Vite + React 18 + TypeScript + Tailwind, aligned with the Claude Design
handoff bundle in `docs/design/`.

## Setup

```bash
cd frontend
npm install
npm run dev          # starts Vite on :5173, proxies /api → :8000
```

## Layout

```
src/
  main.tsx                 React entry (TanStack Query provider)
  App.tsx                  7-tab shell
  index.css                Tailwind + design tokens import
  styles/
    design-tokens.css      verbatim from docs/design/colors_and_type.css
  components/
    Header.tsx             gradient brand bar
    TabNav.tsx             7-tab navigation
    Card.tsx               ds-card wrapper
    VerdictBadge.tsx       Mode 1 + Mode 2 severity badges
  tabs/
    DashboardTab.tsx       quick stats + Phase 0 status
    UploadTab.tsx          drag-drop + spec v2 §6 explainer
    TracesTab.tsx          (Phase 2) Plotly mag/phase/Δ plots
    ComparisonTab.tsx      per-band index table (mocked)
    DiagnosisTab.tsx       (Phase 3) failure mode panel
    ModelingTab.tsx        (Phase 3) pole/Nyquist/ladder
    ReportTab.tsx          (Phase 3) PDF + XLSX export
```

## Design system

Tokens live in `src/styles/design-tokens.css` (Inter + JetBrains Mono,
Tailwind blue brand, slate neutrals, semantic verdict colors, dark mode).
The Tailwind config in `tailwind.config.cjs` mirrors the same scale so
you can use either CSS custom properties (`var(--color-brand-600)`) or
Tailwind utilities (`bg-brand-600`).
