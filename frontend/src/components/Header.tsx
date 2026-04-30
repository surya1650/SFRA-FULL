interface HeaderProps {
  dark: boolean;
  onToggleDark: () => void;
}

export function Header({ dark, onToggleDark }: HeaderProps) {
  return (
    <header
      className="text-white shadow-card"
      style={{
        background:
          "linear-gradient(90deg, var(--color-brand-900), var(--color-brand-600))",
      }}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <div>
          <div className="text-xl font-bold tracking-tight">
            SFRA Diagnostic Tool · APTRANSCO
          </div>
          <div className="mt-0.5 text-xs text-brand-50/80">
            Sweep Frequency Response Analysis for power transformers ·
            CIGRE TB 342 / IEC 60076-18 / IEEE C57.149
          </div>
        </div>
        <button
          type="button"
          onClick={onToggleDark}
          className="rounded bg-white/10 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-white/20"
        >
          {dark ? "☀ Light" : "🌙 Dark"}
        </button>
      </div>
    </header>
  );
}
