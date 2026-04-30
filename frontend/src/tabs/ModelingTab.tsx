import { Card } from "../components/Card";

export function ModelingTab() {
  return (
    <Card
      title="Transfer Function Modeling"
      subtitle="Phase 3 — pole/zero plot, Nyquist, equivalent ladder RLC"
    >
      <p
        className="text-sm"
        style={{ color: "var(--text-secondary)" }}
      >
        Spec v2 §7.4 advisory pole fit (`scipy.signal.invfreqs` order
        search) is already populated on every Mode 1 AnalysisOutcome. The
        UI rendering — pole/zero scatter, Nyquist, ladder fit table — lands
        in Phase 3.
      </p>
    </Card>
  );
}
