import { Card } from "../components/Card";

export function ReportTab() {
  return (
    <Card
      title="Report Export"
      subtitle="Phase 3 — APTRANSCO-letterhead PDF + XLSX"
    >
      <div className="space-y-3 text-sm">
        <p style={{ color: "var(--text-secondary)" }}>
          The PDF report generator preserves the upstream ReportLab structure
          and adds:
        </p>
        <ul
          className="list-inside list-disc space-y-1"
          style={{ color: "var(--text-secondary)" }}
        >
          <li>APTRANSCO letterhead slot (logo from <code>assets/branding/</code>).</li>
          <li>One page per combination · 4-panel plot + indices + remarks.</li>
          <li>Rollup table · overall verdict = worst-of-bands.</li>
          <li>
            DRAFT — INCOMPLETE watermark when the combination set is partially
            populated (spec v2 §11 non-blocking UI rule).
          </li>
        </ul>
        <div className="flex gap-2 opacity-50">
          <button type="button" className="ds-btn-primary" disabled>
            Download PDF
          </button>
          <button type="button" className="ds-btn-secondary" disabled>
            Download XLSX
          </button>
        </div>
      </div>
    </Card>
  );
}
