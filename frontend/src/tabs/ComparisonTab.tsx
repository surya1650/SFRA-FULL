import { Card } from "../components/Card";
import { VerdictBadge } from "../components/VerdictBadge";

export function ComparisonTab() {
  // Mocked rendering until Phase 2 wires /api/analyse.
  const bands = [
    { code: "LOW", range: "20 Hz – 2 kHz", cc: "—", rl: "—", asle: "—", verdict: "INDETERMINATE" as const },
    { code: "MID_L", range: "2 – 20 kHz", cc: "—", rl: "—", asle: "—", verdict: "INDETERMINATE" as const },
    { code: "MID", range: "20 – 400 kHz", cc: "—", rl: "—", asle: "—", verdict: "INDETERMINATE" as const },
    { code: "HIGH", range: "400 kHz – 1 MHz", cc: "—", rl: "—", asle: "—", verdict: "INDETERMINATE" as const },
  ];

  return (
    <div className="space-y-4">
      <Card
        title="Per-band statistical indices"
        subtitle="Spec v2 §7.3 · CC (uncentered) · ASLE · CSD · RL · Max Δ"
      >
        <table className="w-full text-sm">
          <thead>
            <tr
              className="border-b text-left"
              style={{ borderColor: "var(--border-strong)" }}
            >
              {["Band", "Range", "CC", "RL", "ASLE", "Verdict"].map((h) => (
                <th
                  key={h}
                  className="ds-label py-2"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {bands.map((b) => (
              <tr
                key={b.code}
                className="border-b"
                style={{ borderColor: "var(--border-default)" }}
              >
                <td className="py-2 font-medium">{b.code}</td>
                <td
                  className="py-2 text-xs"
                  style={{ color: "var(--text-tertiary)" }}
                >
                  {b.range}
                </td>
                <td className="ds-mono py-2">{b.cc}</td>
                <td className="ds-mono py-2">{b.rl}</td>
                <td className="ds-mono py-2">{b.asle}</td>
                <td className="py-2">
                  <VerdictBadge severity={b.verdict} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
