import { Card } from "../components/Card";

export function TracesTab() {
  return (
    <Card
      title="Traces & Graphs"
      subtitle="Plotly.js magnitude / phase / Δ plots — wired in Phase 2 with /api/traces"
    >
      <div
        className="flex h-72 items-center justify-center rounded text-sm"
        style={{
          background: "var(--surface-card)",
          color: "var(--text-tertiary)",
          border: "1px dashed var(--border-default)",
        }}
      >
        Magnitude / phase / Δ plot placeholder · log-scale X · band shading
      </div>
    </Card>
  );
}
