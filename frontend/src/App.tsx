import { useState } from "react";
import { Header } from "./components/Header";
import { TabNav, type TabKey, TABS } from "./components/TabNav";
import { DashboardTab } from "./tabs/DashboardTab";
import { UploadTab } from "./tabs/UploadTab";
import { TracesTab } from "./tabs/TracesTab";
import { ComparisonTab } from "./tabs/ComparisonTab";
import { DiagnosisTab } from "./tabs/DiagnosisTab";
import { ModelingTab } from "./tabs/ModelingTab";
import { ReportTab } from "./tabs/ReportTab";

export default function App() {
  const [tab, setTab] = useState<TabKey>("dashboard");
  const [dark, setDark] = useState(false);

  return (
    <div
      className={dark ? "dark" : ""}
      style={{ background: "var(--surface-page)", minHeight: "100vh" }}
    >
      <Header dark={dark} onToggleDark={() => setDark((d) => !d)} />
      <TabNav active={tab} onChange={setTab} />
      <main className="mx-auto max-w-7xl px-6 py-6">
        {tab === "dashboard" && <DashboardTab onNavigate={setTab} />}
        {tab === "upload" && <UploadTab />}
        {tab === "traces" && <TracesTab />}
        {tab === "comparison" && <ComparisonTab />}
        {tab === "diagnosis" && <DiagnosisTab />}
        {tab === "modeling" && <ModelingTab />}
        {tab === "report" && <ReportTab />}
      </main>
      <footer
        className="mx-auto max-w-7xl px-6 py-3 text-center text-xs"
        style={{ color: "var(--text-tertiary)" }}
      >
        APTRANSCO SFRA Diagnostic Tool · {TABS.length} tabs · Spec v2 ·
        Mode 1 (comparative) + Mode 2 (single-trace)
      </footer>
    </div>
  );
}
