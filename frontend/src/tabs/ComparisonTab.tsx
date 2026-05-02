import { useMemo, useState } from "react";
import { Card } from "../components/Card";
import { VerdictBadge } from "../components/VerdictBadge";
import { SfraPlot } from "../components/SfraPlot";
import { DiffPlot } from "../components/DiffPlot";
import {
  useSessionAnalyses,
  useSessionTraces,
  useTransformers,
  useTransformerSessions,
} from "../api/hooks";

/**
 * 4-panel comparison view per spec v2 §8 + §10.
 *
 * Layout:
 *   - Top:    Magnitude (ref + tested superimposed)
 *   - Middle: Phase (ref + tested superimposed)
 *   - Below:  Δ (test − ref) with ±3/6 dB watch/alarm lines
 *   - Right:  Per-band metrics + auto-remarks for the selected analysis row
 *
 * Selection flow:
 *   1. Pick a transformer.
 *   2. Pick a session.
 *   3. Pick an analysis row → drives the plots + indices panel.
 */
export function ComparisonTab() {
  const transformers = useTransformers();
  const [transformerId, setTransformerId] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [analysisId, setAnalysisId] = useState<string | null>(null);

  const sessions = useTransformerSessions(transformerId);
  const analyses = useSessionAnalyses(sessionId);
  const traces = useSessionTraces(sessionId);

  const selectedAnalysis = useMemo(
    () => analyses.data?.find((a) => a.id === analysisId) ?? null,
    [analyses.data, analysisId],
  );

  const perBand = useMemo(() => {
    const ind = selectedAnalysis?.indicators_json as
      | { per_band?: Array<Record<string, unknown>> }
      | null
      | undefined;
    return Array.isArray(ind?.per_band) ? ind!.per_band : [];
  }, [selectedAnalysis]);

  return (
    <div className="space-y-4">
      <Card title="1 · Pick a transformer + session + analysis">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3 text-sm">
          <label>
            <span className="ds-label">Transformer</span>
            <select
              className="mt-1 w-full rounded border px-2 py-1.5 text-sm"
              style={{ borderColor: "var(--border-default)" }}
              value={transformerId ?? ""}
              onChange={(e) => {
                setTransformerId(e.target.value || null);
                setSessionId(null);
                setAnalysisId(null);
              }}
            >
              <option value="">— select —</option>
              {transformers.data?.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.serial_no} ({t.transformer_type})
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="ds-label">Session</span>
            <select
              className="mt-1 w-full rounded border px-2 py-1.5 text-sm"
              style={{ borderColor: "var(--border-default)" }}
              value={sessionId ?? ""}
              onChange={(e) => {
                setSessionId(e.target.value || null);
                setAnalysisId(null);
              }}
              disabled={!transformerId}
            >
              <option value="">— select —</option>
              {sessions.data?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.session_date} ({s.session_type})
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="ds-label">Analysis row</span>
            <select
              className="mt-1 w-full rounded border px-2 py-1.5 text-sm"
              style={{ borderColor: "var(--border-default)" }}
              value={analysisId ?? ""}
              onChange={(e) => setAnalysisId(e.target.value || null)}
              disabled={!sessionId}
            >
              <option value="">— select —</option>
              {analyses.data?.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.severity} · {a.mode} · {a.id.slice(0, 8)}
                </option>
              ))}
            </select>
          </label>
        </div>
        {selectedAnalysis && (
          <div className="mt-3 flex items-center gap-2 text-sm">
            <VerdictBadge severity={selectedAnalysis.severity} />
            <span style={{ color: "var(--text-tertiary)" }}>
              tested={selectedAnalysis.tested_trace_id.slice(0, 8)}{" "}
              {selectedAnalysis.reference_trace_id
                ? `· ref=${selectedAnalysis.reference_trace_id.slice(0, 8)}`
                : "· no reference (Mode 2)"}
            </span>
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Magnitude · tested" subtitle="log-Hz · spec v2 §8 panel 1">
          <SfraPlot traceId={selectedAnalysis?.tested_trace_id ?? null} mode="magnitude" />
        </Card>
        <Card title="Magnitude · reference" subtitle="superimpose vs tested in §10 PDF">
          <SfraPlot traceId={selectedAnalysis?.reference_trace_id ?? null} mode="magnitude" />
        </Card>
        <Card title="Phase · tested" subtitle="unwrapped">
          <SfraPlot traceId={selectedAnalysis?.tested_trace_id ?? null} mode="phase" />
        </Card>
        <Card title="Δ (test − ref)" subtitle="±3 dB watch · ±6 dB alarm">
          <DiffPlot
            referenceTraceId={selectedAnalysis?.reference_trace_id ?? null}
            testedTraceId={selectedAnalysis?.tested_trace_id ?? null}
          />
        </Card>
      </div>

      {selectedAnalysis && (
        <Card
          title="Per-band metrics + auto-remark"
          subtitle="spec v2 §7.3 indices · DL/T 911 RL thresholds"
        >
          {perBand.length === 0 && selectedAnalysis.mode === "reference_missing_analysis" && (
            <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
              Mode 2 (single trace, no reference). Per-band statistical metrics
              are unavailable until a reference is uploaded into this cycle.
            </p>
          )}
          {perBand.length > 0 && (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left" style={{ borderColor: "var(--border-strong)" }}>
                  {["Band", "n", "CC", "RL", "ASLE", "CSD", "MaxΔ dB", "@ Hz"].map((h) => (
                    <th key={h} className="ds-label py-2">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {perBand.map((b: Record<string, unknown>, i) => (
                  <tr key={i} className="border-b" style={{ borderColor: "var(--border-default)" }}>
                    <td className="py-2 font-medium">{String(b.band_code ?? "")}</td>
                    <td className="ds-mono py-2">{String(b.n_points ?? "—")}</td>
                    <td className="ds-mono py-2">{_fmt(b.cc, 4)}</td>
                    <td className="ds-mono py-2">{_fmt(b.rl_factor, 2)}</td>
                    <td className="ds-mono py-2">{_fmt(b.asle, 3)}</td>
                    <td className="ds-mono py-2">{_fmt(b.csd, 3)}</td>
                    <td className="ds-mono py-2">{_fmt(b.max_dev_db, 2)}</td>
                    <td className="ds-mono py-2">{_fmtFreq(b.max_dev_freq_hz)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {selectedAnalysis.auto_remarks && (
            <div
              className="mt-3 rounded p-3 text-sm"
              style={{ background: "var(--surface-card)", color: "var(--text-secondary)" }}
            >
              <strong>Auto-remark:</strong> {selectedAnalysis.auto_remarks}
            </div>
          )}
        </Card>
      )}

      {traces.data && traces.data.length > 0 && (
        <Card
          title={`Session traces · ${traces.data.length}`}
          subtitle="REFERENCE + TESTED — newest first"
        >
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left" style={{ borderColor: "var(--border-strong)" }}>
                {["Role", "Label", "Combo", "n_pts", "f range", "Format"].map((h) => (
                  <th key={h} className="ds-label py-2">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {traces.data.map((t) => (
                <tr key={t.id} className="border-b" style={{ borderColor: "var(--border-default)" }}>
                  <td className="py-2">{t.role}</td>
                  <td className="py-2">{t.label}</td>
                  <td className="py-2">{t.combination_id ?? "—"}</td>
                  <td className="ds-mono py-2">{t.point_count}</td>
                  <td className="ds-mono py-2 text-xs">
                    {t.freq_min_hz.toFixed(0)}–{(t.freq_max_hz / 1e6).toFixed(2)}M Hz
                  </td>
                  <td className="text-xs">{t.source_file_format}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}

function _fmt(v: unknown, digits: number): string {
  if (typeof v !== "number" || !Number.isFinite(v)) return "—";
  const a = Math.abs(v);
  if (a !== 0 && (a < 1e-3 || a >= 1e4)) return v.toExponential(2);
  return v.toFixed(digits);
}

function _fmtFreq(v: unknown): string {
  if (typeof v !== "number" || !Number.isFinite(v)) return "—";
  if (v >= 1_000_000) return `${(v / 1e6).toFixed(2)} MHz`;
  if (v >= 1_000) return `${(v / 1e3).toFixed(1)} kHz`;
  return `${v.toFixed(0)} Hz`;
}
