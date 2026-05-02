/**
 * Difference plot — (test - reference) magnitude in dB.
 *
 * Renders ±3 dB watch lines and ±6 dB alarm lines per spec v2 §8 panel 2.
 * Lazy-loads Plotly the same way SfraPlot does.
 */
import { useEffect, useRef } from "react";
import { useTraceData } from "../api/hooks";

interface DiffPlotProps {
  referenceTraceId: string | null;
  testedTraceId: string | null;
  height?: number;
}

export function DiffPlot({
  referenceTraceId,
  testedTraceId,
  height = 240,
}: DiffPlotProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const ref = useTraceData(referenceTraceId);
  const tested = useTraceData(testedTraceId);

  useEffect(() => {
    const el = containerRef.current;
    if (!el || !ref.data || !tested.data) return;

    let cancelled = false;
    void import("plotly.js-dist-min").then((mod) => {
      if (cancelled) return;
      const Plotly = (mod as unknown as { default: typeof import("plotly.js-dist-min").default }).default ?? mod;

      // Interpolate the reference onto the tested grid (linear in log-Hz).
      const f = tested.data!.frequency_hz;
      const m = tested.data!.magnitude_db;
      const fr = ref.data!.frequency_hz;
      const mr = ref.data!.magnitude_db;
      const diff = f.map((fi, i) => {
        const j = _binarySearch(fr, fi);
        if (j <= 0 || j >= fr.length) return NaN;
        const t = (Math.log10(fi) - Math.log10(fr[j - 1])) /
                  (Math.log10(fr[j]) - Math.log10(fr[j - 1]));
        const interp = mr[j - 1] + t * (mr[j] - mr[j - 1]);
        return m[i] - interp;
      });

      const layout: Partial<Parameters<typeof Plotly.newPlot>[2]> = {
        height,
        margin: { l: 56, r: 24, t: 24, b: 40 },
        xaxis: {
          type: "log",
          title: { text: "Frequency (Hz)" },
          gridcolor: "#e2e8f0",
        },
        yaxis: {
          title: { text: "Δ Magnitude (dB)" },
          gridcolor: "#e2e8f0",
          zeroline: true,
          zerolinecolor: "#94a3b8",
          zerolinewidth: 1,
        },
        shapes: [
          { type: "line", xref: "paper", yref: "y", x0: 0, x1: 1, y0: 3, y1: 3, line: { color: "#f59e0b", width: 1, dash: "dash" } },
          { type: "line", xref: "paper", yref: "y", x0: 0, x1: 1, y0: -3, y1: -3, line: { color: "#f59e0b", width: 1, dash: "dash" } },
          { type: "line", xref: "paper", yref: "y", x0: 0, x1: 1, y0: 6, y1: 6, line: { color: "#f43f5e", width: 1, dash: "dot" } },
          { type: "line", xref: "paper", yref: "y", x0: 0, x1: 1, y0: -6, y1: -6, line: { color: "#f43f5e", width: 1, dash: "dot" } },
        ],
        showlegend: false,
        plot_bgcolor: "rgba(0,0,0,0)",
        paper_bgcolor: "rgba(0,0,0,0)",
      };

      void Plotly.newPlot(
        el,
        [{
          x: f,
          y: diff,
          type: "scatter",
          mode: "lines",
          name: "Δ",
          line: { color: "#3b82f6", width: 2 },
        }],
        layout,
        { responsive: true, displaylogo: false },
      );
    });

    return () => {
      cancelled = true;
      if (el) {
        void import("plotly.js-dist-min").then((mod) => {
          const Plotly = (mod as unknown as { default: typeof import("plotly.js-dist-min").default }).default ?? mod;
          try { Plotly.purge(el); } catch { /* noop */ }
        });
      }
    };
  }, [ref.data, tested.data, height]);

  if (!referenceTraceId || !testedTraceId) {
    return (
      <div style={{ height, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-tertiary)", fontSize: 13 }}>
        Select both a reference and a tested trace.
      </div>
    );
  }
  if (ref.isLoading || tested.isLoading) {
    return <div style={{ height, display: "flex", alignItems: "center", justifyContent: "center" }}>Loading…</div>;
  }
  return <div ref={containerRef} style={{ width: "100%", height }} />;
}

function _binarySearch(arr: number[], target: number): number {
  // Returns the smallest index j such that arr[j] >= target, or arr.length.
  let lo = 0;
  let hi = arr.length;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (arr[mid] < target) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}
