import { Card } from "../components/Card";

export function DiagnosisTab() {
  return (
    <Card
      title="Failure Diagnosis"
      subtitle="Phase 3 — failure-mode rule registry + multi-standard verdicts"
    >
      <p
        className="text-sm"
        style={{ color: "var(--text-secondary)" }}
      >
        The deterministic rule registry will land in Phase 3. The Phase 0
        analysis runner already emits an auto-remark per spec v2 §7.7 with
        the worst affected band's root-cause hint.
      </p>
    </Card>
  );
}
