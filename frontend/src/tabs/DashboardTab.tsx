import { Card } from "../components/Card";
import { VerdictBadge } from "../components/VerdictBadge";
import type { TabKey } from "../components/TabNav";

interface Props {
  onNavigate: (k: TabKey) => void;
}

export function DashboardTab({ onNavigate }: Props) {
  // Phase 0 — wired-up data integration in Phase 2 once the API is up.
  const stats = [
    { label: "Transformers", value: "—", sub: "Phase 2" },
    { label: "Open cycles", value: "—", sub: "Phase 2" },
    { label: "Pending Mode 2", value: "—", sub: "single-trace queue" },
    { label: "Standards", value: "3", sub: "CIGRE / IEC / IEEE" },
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
            <div
              className="mt-1 text-xs"
              style={{ color: "var(--text-tertiary)" }}
            >
              {s.sub}
            </div>
          </Card>
        ))}
      </div>
      <Card title="Phase 0 status" subtitle="What's working today">
        <ul className="space-y-2 text-sm">
          <li className="flex items-center gap-2">
            <VerdictBadge severity="NORMAL" />
            <span>
              Combination catalogue (15 + 21 + 12 = 48 combinations)
            </span>
          </li>
          <li className="flex items-center gap-2">
            <VerdictBadge severity="NORMAL" />
            <span>FRAX + CSV parsers, combination resolver</span>
          </li>
          <li className="flex items-center gap-2">
            <VerdictBadge severity="NORMAL" />
            <span>Mode 1 (comparative) + Mode 2 (single-trace) analysis</span>
          </li>
          <li className="flex items-center gap-2">
            <VerdictBadge severity="SUSPECT" />
            <span>Mode 2 standalone is qualitative — re-run as Mode 1 once a reference is uploaded</span>
          </li>
          <li className="flex items-center gap-2">
            <VerdictBadge severity="INDETERMINATE" />
            <span>API + DB layer + per-combination grid land in Phase 2</span>
          </li>
        </ul>
        <div className="mt-4 flex gap-2">
          <button
            type="button"
            className="ds-btn-primary"
            onClick={() => onNavigate("upload")}
          >
            Upload trace
          </button>
          <button
            type="button"
            className="ds-btn-secondary"
            onClick={() => onNavigate("comparison")}
          >
            View comparison
          </button>
        </div>
      </Card>
    </div>
  );
}
