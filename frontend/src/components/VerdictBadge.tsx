import clsx from "clsx";

/** Spec v2 §3 severity enum + Mode 2 qualitative severities. */
export type Severity =
  | "NORMAL"
  | "MINOR_DEVIATION"
  | "SIGNIFICANT_DEVIATION"
  | "SEVERE_DEVIATION"
  | "APPEARS_NORMAL"
  | "SUSPECT"
  | "INDETERMINATE";

const STYLE: Record<Severity, string> = {
  NORMAL: "bg-emerald-100 text-emerald-800",
  MINOR_DEVIATION: "bg-amber-100 text-amber-800",
  SIGNIFICANT_DEVIATION: "bg-orange-100 text-orange-800",
  SEVERE_DEVIATION: "bg-rose-100 text-rose-800",
  APPEARS_NORMAL: "bg-emerald-100 text-emerald-800",
  SUSPECT: "bg-amber-100 text-amber-800",
  INDETERMINATE: "bg-slate-100 text-slate-700",
};

const LABEL: Record<Severity, string> = {
  NORMAL: "Normal",
  MINOR_DEVIATION: "Minor",
  SIGNIFICANT_DEVIATION: "Significant",
  SEVERE_DEVIATION: "Severe",
  APPEARS_NORMAL: "Appears Normal",
  SUSPECT: "Suspect",
  INDETERMINATE: "Indeterminate",
};

interface Props {
  severity: Severity;
  className?: string;
}

export function VerdictBadge({ severity, className }: Props) {
  return (
    <span
      className={clsx(
        "rounded px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide",
        STYLE[severity] ?? STYLE.INDETERMINATE,
        className,
      )}
    >
      {LABEL[severity] ?? severity}
    </span>
  );
}
