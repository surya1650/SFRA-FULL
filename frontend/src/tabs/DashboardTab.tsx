import { Card } from "../components/Card";
import { VerdictBadge } from "../components/VerdictBadge";
import type { TabKey } from "../components/TabNav";
import { useHealth, useTransformers } from "../api/hooks";
import type { Severity } from "../api/client";

interface Props {
  onNavigate: (k: TabKey) => void;
}

export function DashboardTab({ onNavigate }: Props) {
  const health = useHealth();
  const transformers = useTransformers();

  const stats = [
    {
      label: "API status",
      value: health.data ? "OK" : health.isError ? "DOWN" : "…",
      sub: health.data?.version ?? "",
    },
    {
      label: "Transformers",
      value: transformers.data ? String(transformers.data.length) : "…",
      sub: transformers.data ? "registered" : "loading",
    },
    {
      label: "Open cycles",
      value: "—",
      sub: "click in to a transformer",
    },
    {
      label: "Standards",
      value: "3",
      sub: "CIGRE / IEC / IEEE",
    },
  ];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {stats.map((s) => (
          <Card key={s.label} className="!p-4">
            <div className="ds-label">{s.label}</div>
            <div
              className="mt-2 text-2xl font-bold"
              style={{ color: "var(--text-primary)" }}
            >
              {s.value}
            </div>
            <div className="mt-1 text-xs" style={{ color: "var(--text-tertiary)" }}>
              {s.sub}
            </div>
          </Card>
        ))}
      </div>

      <Card title="Transformers" subtitle="Click to view cycles + sessions">
        {transformers.isLoading && (
          <div className="text-sm" style={{ color: "var(--text-tertiary)" }}>
            Loading…
          </div>
        )}
        {transformers.isError && (
          <div className="text-sm text-rose-600">
            Failed to load: {String(transformers.error)}
          </div>
        )}
        {transformers.data && transformers.data.length === 0 && (
          <div className="text-sm" style={{ color: "var(--text-secondary)" }}>
            No transformers registered yet.{" "}
            <button
              type="button"
              className="text-brand-600 hover:underline"
              onClick={() => onNavigate("upload")}
            >
              Register one →
            </button>
          </div>
        )}
        {transformers.data && transformers.data.length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr
                className="border-b text-left"
                style={{ borderColor: "var(--border-strong)" }}
              >
                {["Serial", "Type", "MVA", "HV/LV", "Substation"].map((h) => (
                  <th key={h} className="ds-label py-2">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {transformers.data.map((t) => (
                <tr
                  key={t.id}
                  className="border-b"
                  style={{ borderColor: "var(--border-default)" }}
                >
                  <td className="py-2 font-medium">{t.serial_no}</td>
                  <td className="py-2 text-xs">{t.transformer_type}</td>
                  <td className="ds-mono py-2">{t.nameplate_mva ?? "—"}</td>
                  <td className="ds-mono py-2">
                    {t.hv_kv ? `${t.hv_kv} / ${t.lv_kv ?? "—"}` : "—"}
                  </td>
                  <td className="py-2 text-xs">{t.substation ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Card title="Phase status" subtitle="What's wired today">
        <ul className="space-y-2 text-sm">
          {[
            { sev: "NORMAL" as Severity, text: "Phase 0 — analysis core (Mode 1 + Mode 2)" },
            { sev: "NORMAL" as Severity, text: "Phase 1 — DB + storage + 16-endpoint API" },
            {
              sev: "MINOR_DEVIATION" as Severity,
              text: "Phase 2 — frontend wiring (this view), Plotly charts, reports",
            },
            { sev: "INDETERMINATE" as Severity, text: "Phase 3 — auth + OEM parsers" },
          ].map((row) => (
            <li key={row.text} className="flex items-center gap-2">
              <VerdictBadge severity={row.sev} />
              <span>{row.text}</span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
