/**
 * Plotly magnitude/phase chart driven by /api/traces/{id}/data.
 *
 * Lazy-loads plotly.js-dist-min so the initial bundle stays small —
 * Plotly is ~3 MB and only the Traces / Comparison tabs need it.
 */
import { useEffect, useRef } from "react";
import { useTraceData } from "../api/hooks";

interface SfraPlotProps {
  traceId: string | null;
  mode?: "magnitude" | "phase";
  showSubbands?: boolean;
  height?: number;
}

const BAND_BOUNDS_HZ: { code: string; lo: number; hi: number; color: string }[] = [
  { code: "LOW",   lo: 20,        hi: 2_000,    color: "rgba(16,185,129,0.08)" },
  { code: "MID_L", lo: 2_000,     hi: 20_000,   color: "rgba(245,158,11,0.08)" },
  { code: "MID",   lo: 20_000,    hi: 400_000,  color: "rgba(249,115,22,0.08)" },
  { code: "HIGH",  lo: 400_000,   hi: 1_000_000, color: "rgba(244,63,94,0.08)" },
];

export function SfraPlot({
  traceId,
  mode = "magnitude",
  showSubbands = true,
  height = 320,
}: SfraPlotProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { data, isLoading, error } = useTraceData(traceId);

  useEffect(() => {
    const el = containerRef.current;
    if (!el || !data) return;

    let cancelled = false;

    void import("plotly.js-dist-min").then((mod) => {
      if (cancelled) return;
      const Plotly = (mod as unknown as { default: typeof import("plotly.js-dist-min").default }).default ?? mod;

      const traces = [
        {
          x: data.frequency_hz,
          y: mode === "magnitude" ? data.magnitude_db : data.phase_deg ?? [],
          type: "scatter" as const,
          mode: "lines" as const,
          name: data.label,
          line: { color: "#3b82f6", width: 2 },
        },
      ];

      const shapes = showSubbands
        ? BAND_BOUNDS_HZ.map((b) => ({
            type: "rect" as const,
            xref: "x" as const,
            yref: "paper" as const,
            x0: b.lo,
            x1: b.hi,
            y0: 0,
            y1: 1,
            line: { width: 0 },
            fillcolor: b.color,
            layer: "below" as const,
          }))
        : [];

      const annotations = showSubbands
        ? BAND_BOUNDS_HZ.map((b) => ({
            x: Math.sqrt(b.lo * b.hi),
            y: 1.0,
            xref: "x" as const,
            yref: "paper" as const,
            text: b.code,
            showarrow: false,
            yshift: 8,
            font: { size: 10, color: "#64748b" },
          }))
        : [];

      const layout: Partial<Parameters<typeof Plotly.newPlot>[2]> = {
        height,
        margin: { l: 56, r: 24, t: 24, b: 40 },
        xaxis: {
          type: "log",
          title: { text: "Frequency (Hz)" },
          gridcolor: "#e2e8f0",
        },
        yaxis: {
          title: { text: mode === "magnitude" ? "Magnitude (dB)" : "Phase (°)" },
          gridcolor: "#e2e8f0",
        },
        shapes,
        annotations,
        showlegend: false,
        plot_bgcolor: "rgba(0,0,0,0)",
        paper_bgcolor: "rgba(0,0,0,0)",
      };

      void Plotly.newPlot(el, traces, layout, {
        responsive: true,
        displaylogo: false,
        modeBarButtonsToRemove: ["lasso2d", "select2d"],
      });
    });

    return () => {
      cancelled = true;
      // Clear plot DOM on unmount to free Plotly resources.
      if (el) {
        void import("plotly.js-dist-min").then((mod) => {
          const Plotly = (mod as unknown as { default: typeof import("plotly.js-dist-min").default }).default ?? mod;
          try {
            Plotly.purge(el);
          } catch {
            /* noop */
          }
        });
      }
    };
  }, [data, mode, showSubbands, height]);

  if (!traceId) {
    return (
      <div
        style={{
          height,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--text-tertiary)",
          fontSize: 13,
        }}
      >
        Select a trace to plot.
      </div>
    );
  }
  if (isLoading) {
    return (
      <div
        style={{ height, display: "flex", alignItems: "center", justifyContent: "center" }}
      >
        Loading trace data…
      </div>
    );
  }
  if (error) {
    return (
      <div style={{ color: "#9f1239", fontSize: 13 }}>
        Failed to load trace data: {String(error)}
      </div>
    );
  }
  return <div ref={containerRef} style={{ width: "100%", height }} />;
}
