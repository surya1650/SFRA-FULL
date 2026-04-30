import clsx from "clsx";

export type TabKey =
  | "dashboard"
  | "upload"
  | "traces"
  | "comparison"
  | "diagnosis"
  | "modeling"
  | "report";

export const TABS: { key: TabKey; label: string }[] = [
  { key: "dashboard", label: "Dashboard" },
  { key: "upload", label: "Upload & Configure" },
  { key: "traces", label: "Traces & Graphs" },
  { key: "comparison", label: "Comparison & Indices" },
  { key: "diagnosis", label: "Failure Diagnosis" },
  { key: "modeling", label: "Modeling" },
  { key: "report", label: "Report" },
];

interface TabNavProps {
  active: TabKey;
  onChange: (k: TabKey) => void;
}

export function TabNav({ active, onChange }: TabNavProps) {
  return (
    <nav
      className="border-b bg-white dark:bg-slate-800"
      style={{ borderColor: "var(--border-default)" }}
    >
      <div className="mx-auto flex max-w-7xl overflow-x-auto px-6">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => onChange(t.key)}
            className={clsx(
              "border-b-2 whitespace-nowrap px-4 py-3 text-sm font-medium transition-colors",
              active === t.key
                ? "border-brand-600 text-brand-700 dark:text-brand-300"
                : "border-transparent text-slate-600 hover:text-brand-600 dark:text-slate-300",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>
    </nav>
  );
}
