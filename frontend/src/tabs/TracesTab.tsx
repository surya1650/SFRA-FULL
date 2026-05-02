import { useEffect, useState } from "react";
import { Card } from "../components/Card";
import { SfraPlot } from "../components/SfraPlot";
import { useTransformers } from "../api/hooks";
import { api } from "../api/client";
import type { Trace } from "../api/client";

export function TracesTab() {
  const transformers = useTransformers();
  const [traceId, setTraceId] = useState<string | null>(null);
  const [traces, setTraces] = useState<Trace[]>([]);

  // Demo discovery: fetch all sessions for the first transformer and surface
  // their traces. Phase 3 replaces this with a richer transformer/session
  // selector UI; for now this proves the wiring end-to-end.
  useEffect(() => {
    let cancelled = false;
    async function loadTraces() {
      if (!transformers.data || transformers.data.length === 0) return;
      const t = transformers.data[0];
      try {
        const cycles = await api.listCycles(t.id);
        const allTraces: Trace[] = [];
        for (const c of cycles) {
          const analyses = c.is_open ? null : null;
          void analyses;
          // Phase 1's API doesn't expose "list sessions for cycle" yet —
          // walk the analyses endpoint via the server-rendered list once
          // we add it. For Phase 2.1 we surface only the most recent
          // tested trace via a future endpoint; placeholder for now.
        }
        if (!cancelled) setTraces(allTraces);
      } catch {
        /* tolerate; demo only */
      }
    }
    void loadTraces();
    return () => {
      cancelled = true;
    };
  }, [transformers.data]);

  return (
    <div className="space-y-4">
      <Card
        title="Trace selector"
        subtitle="Plotly chart wired to GET /api/traces/{id}/data"
      >
        {traces.length === 0 ? (
          <div
            className="rounded border-2 border-dashed py-8 text-center text-sm"
            style={{
              borderColor: "var(--border-default)",
              color: "var(--text-tertiary)",
            }}
          >
            Upload a trace via the <strong>Upload &amp; Configure</strong> tab,
            then paste its trace id below to render the chart.
          </div>
        ) : (
          <ul className="space-y-1">
            {traces.map((t) => (
              <li key={t.id}>
                <button
                  type="button"
                  onClick={() => setTraceId(t.id)}
                  className={
                    "w-full rounded px-2 py-1 text-left text-sm hover:bg-slate-100 dark:hover:bg-slate-700"
                  }
                >
                  {t.label} <span className="ds-mono text-xs">{t.id.slice(0, 8)}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
        <div className="mt-3 grid grid-cols-[1fr_auto] gap-2">
          <input
            placeholder="paste trace id…"
            value={traceId ?? ""}
            onChange={(e) => setTraceId(e.target.value || null)}
            className="rounded border px-2 py-1.5 text-sm"
            style={{ borderColor: "var(--border-default)" }}
          />
          <button
            type="button"
            className="ds-btn-secondary"
            onClick={() => setTraceId(null)}
          >
            Clear
          </button>
        </div>
      </Card>

      <Card title="Magnitude (dB)" subtitle="log-scale frequency · band shading">
        <SfraPlot traceId={traceId} mode="magnitude" />
      </Card>

      <Card title="Phase (°)" subtitle="unwrapped phase">
        <SfraPlot traceId={traceId} mode="phase" />
      </Card>
    </div>
  );
}
