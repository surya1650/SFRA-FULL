import { useCallback, useMemo, useState } from "react";
import { useDropzone } from "react-dropzone";
import clsx from "clsx";
import { Card } from "../components/Card";
import {
  useCombinations,
  useCreateCycle,
  useCreateSession,
  useCreateTransformer,
  useTransformers,
  useUploadToSession,
  useAnalyseSession,
  useSessionAnalyses,
} from "../api/hooks";
import type {
  TraceRole,
  TransformerType,
  UnmappedSweep,
  UploadResponse,
} from "../api/client";
import { VerdictBadge } from "../components/VerdictBadge";

const TRANSFORMER_TYPES: TransformerType[] = [
  "TWO_WINDING",
  "AUTO_WITH_TERTIARY_BROUGHT_OUT",
  "AUTO_WITH_TERTIARY_BURIED",
  "THREE_WINDING",
];

export function UploadTab() {
  const [serial, setSerial] = useState("TR-DEMO-1");
  const [type, setType] = useState<TransformerType>("TWO_WINDING");
  const [transformerId, setTransformerId] = useState<string | null>(null);
  const [cycleId, setCycleId] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [combinationCode, setCombinationCode] = useState<string>("EEOC_HV_R");
  const [role, setRole] = useState<TraceRole>("TESTED");
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const transformers = useTransformers();
  const combinations = useCombinations(type);
  const createTransformer = useCreateTransformer();
  const createCycle = useCreateCycle(transformerId ?? "");
  const createSession = useCreateSession(transformerId ?? "");
  const uploadMutation = useUploadToSession(sessionId ?? "");
  const analyseMutation = useAnalyseSession(sessionId ?? "");
  const sessionAnalyses = useSessionAnalyses(sessionId);

  const onDrop = useCallback(
    async (accepted: File[]) => {
      setErrorMsg(null);
      if (!sessionId) {
        setErrorMsg("Create a transformer + cycle + session first.");
        return;
      }
      if (accepted.length === 0) return;
      try {
        const res = await uploadMutation.mutateAsync({
          file: accepted[0],
          params: {
            role,
            combination_code: combinationCode || undefined,
          },
        });
        setUploadResult(res);
      } catch (err) {
        setErrorMsg(String(err));
      }
    },
    [sessionId, role, combinationCode, uploadMutation],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/octet-stream": [".frax", ".xfra", ".fra", ".sfra"],
      "text/csv": [".csv", ".tsv"],
      "text/xml": [".xml"],
    },
    multiple: false,
  });

  const today = useMemo(() => new Date().toISOString().slice(0, 10), []);

  const wireUp = async () => {
    setErrorMsg(null);
    try {
      const t = await createTransformer.mutateAsync({
        serial_no: serial,
        transformer_type: type,
      });
      setTransformerId(t.id);
      const cyc = await createCycle.mutateAsync({
        intervention_type: "COMMISSIONING",
        cycle_start_date: today,
      });
      setCycleId(cyc.id);
      // Now create the session (need fresh transformer id).
      const sess = await createSession.mutateAsync({
        overhaul_cycle_id: cyc.id,
        session_type: "ROUTINE",
        session_date: today,
      });
      setSessionId(sess.id);
    } catch (err) {
      setErrorMsg(String(err));
    }
  };

  const runAnalysis = async () => {
    setErrorMsg(null);
    try {
      await analyseMutation.mutateAsync();
    } catch (err) {
      setErrorMsg(String(err));
    }
  };

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Card title="1 · Register transformer + open cycle + session">
        <div className="grid grid-cols-2 gap-3 text-sm">
          <label className="block">
            <span className="ds-label">Serial</span>
            <input
              value={serial}
              onChange={(e) => setSerial(e.target.value)}
              className="mt-1 w-full rounded border px-2 py-1.5 text-sm"
              style={{ borderColor: "var(--border-default)" }}
            />
          </label>
          <label className="block">
            <span className="ds-label">Type</span>
            <select
              value={type}
              onChange={(e) => setType(e.target.value as TransformerType)}
              className="mt-1 w-full rounded border px-2 py-1.5 text-sm"
              style={{ borderColor: "var(--border-default)" }}
            >
              {TRANSFORMER_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="mt-3">
          <button
            type="button"
            className="ds-btn-primary"
            onClick={wireUp}
            disabled={!!sessionId}
          >
            {sessionId ? "Session ready ✓" : "Create + open cycle + start session"}
          </button>
        </div>
        {transformerId && (
          <div className="mt-3 text-xs" style={{ color: "var(--text-tertiary)" }}>
            transformer={transformerId.slice(0, 8)} ·
            cycle={cycleId?.slice(0, 8)} ·
            session={sessionId?.slice(0, 8)}
          </div>
        )}
        {transformers.data && transformers.data.length > 0 && (
          <div className="mt-3 text-xs" style={{ color: "var(--text-tertiary)" }}>
            {transformers.data.length} transformer(s) registered.
          </div>
        )}
      </Card>

      <Card title="2 · Upload SFRA file">
        <div className="mb-3 grid grid-cols-2 gap-3 text-sm">
          <label className="block">
            <span className="ds-label">Role</span>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as TraceRole)}
              className="mt-1 w-full rounded border px-2 py-1.5 text-sm"
              style={{ borderColor: "var(--border-default)" }}
            >
              <option value="TESTED">TESTED</option>
              <option value="REFERENCE">REFERENCE</option>
            </select>
          </label>
          <label className="block">
            <span className="ds-label">Combination code</span>
            <select
              value={combinationCode}
              onChange={(e) => setCombinationCode(e.target.value)}
              className="mt-1 w-full rounded border px-2 py-1.5 text-sm"
              style={{ borderColor: "var(--border-default)" }}
            >
              <option value="">(auto-detect from FRAX properties)</option>
              {combinations.data?.map((c) => (
                <option key={c.code} value={c.code}>
                  {c.code} — {c.description?.slice(0, 40)}…
                </option>
              ))}
            </select>
          </label>
        </div>
        <div
          {...getRootProps()}
          className={clsx(
            "rounded-lg border-2 border-dashed px-5 py-10 text-center transition-colors cursor-pointer",
            isDragActive
              ? "border-brand-600 bg-brand-50 dark:bg-slate-700"
              : "border-slate-300 dark:border-slate-600",
            !sessionId && "opacity-50 pointer-events-none",
          )}
        >
          <input {...getInputProps()} />
          <div className="mb-2 text-3xl">📂</div>
          <div className="text-sm font-semibold">
            {!sessionId
              ? "Create a session first ↑"
              : isDragActive
                ? "Drop now…"
                : "Drop SFRA file here, or click to browse"}
          </div>
          <div className="mt-1 text-xs" style={{ color: "var(--text-tertiary)" }}>
            .frax · .xfra · .fra · .sfra · .csv · .tsv · .xml
          </div>
        </div>

        {uploadMutation.isPending && (
          <div className="mt-3 text-sm" style={{ color: "var(--text-tertiary)" }}>
            Uploading…
          </div>
        )}
        {errorMsg && (
          <div className="mt-3 text-sm text-rose-600">Error: {errorMsg}</div>
        )}
      </Card>

      {uploadResult && (
        <Card
          title="3 · Upload result"
          subtitle={`detected_format=${uploadResult.detected_format} · ${uploadResult.n_traces_persisted} trace(s) persisted`}
          className="lg:col-span-2"
        >
          <div className="space-y-2 text-sm">
            {uploadResult.traces.map((t) => (
              <div
                key={t.id}
                className="flex items-center justify-between border-b py-1.5"
                style={{ borderColor: "var(--border-default)" }}
              >
                <div>
                  <span className="font-medium">{t.label}</span>
                  <span
                    className="ml-2 ds-mono text-xs"
                    style={{ color: "var(--text-tertiary)" }}
                  >
                    {t.point_count} pts · {t.freq_min_hz.toFixed(0)}–
                    {(t.freq_max_hz / 1e6).toFixed(2)}M Hz
                  </span>
                </div>
                <span
                  className="ds-mono text-xs"
                  style={{ color: "var(--text-tertiary)" }}
                >
                  sha={t.source_file_sha256?.slice(0, 8)}
                </span>
              </div>
            ))}
            {uploadResult.unmapped_sweeps.length > 0 && (
              <div className="rounded bg-amber-50 p-2 text-xs text-amber-800">
                {uploadResult.unmapped_sweeps.length} unmapped sweep(s) — assign manually:
                <ul className="mt-1 list-disc pl-5">
                  {uploadResult.unmapped_sweeps.map((u: UnmappedSweep, i) => (
                    <li key={i}>
                      {u.label} (suggested: {u.suggested_code ?? "—"}) — {u.reason}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <div className="flex gap-2 pt-2">
              <button
                type="button"
                className="ds-btn-primary"
                onClick={runAnalysis}
                disabled={analyseMutation.isPending}
              >
                {analyseMutation.isPending ? "Analysing…" : "Run analysis (Mode 1/2)"}
              </button>
            </div>
          </div>
        </Card>
      )}

      {sessionAnalyses.data && sessionAnalyses.data.length > 0 && (
        <Card
          title="4 · Analysis results"
          subtitle={`${sessionAnalyses.data.length} result(s) for this session`}
          className="lg:col-span-2"
        >
          <div className="space-y-2 text-sm">
            {sessionAnalyses.data.map((a) => (
              <div
                key={a.id}
                className="border-b py-2"
                style={{ borderColor: "var(--border-default)" }}
              >
                <div className="flex items-center gap-2">
                  <VerdictBadge severity={a.severity} />
                  <span className="text-xs uppercase tracking-wide">
                    {a.mode}
                  </span>
                  <span
                    className="ds-mono text-xs"
                    style={{ color: "var(--text-tertiary)" }}
                  >
                    tested={a.tested_trace_id.slice(0, 8)}
                    {a.reference_trace_id
                      ? ` ref=${a.reference_trace_id.slice(0, 8)}`
                      : " (no reference)"}
                  </span>
                </div>
                {a.auto_remarks && (
                  <p
                    className="mt-1 text-xs"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    {a.auto_remarks}
                  </p>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
