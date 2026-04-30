/** Tailwind config aligned with docs/design/DESIGN_SYSTEM.md tokens. */
module.exports = {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx,js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "Fira Code", "Consolas", "monospace"],
      },
      colors: {
        // Brand (Tailwind blue scale, design-system aligned).
        brand: {
          50: "#eff6ff",
          100: "#dbeafe",
          200: "#bfdbfe",
          300: "#93c5fd",
          400: "#60a5fa",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
          800: "#1e40af",
          900: "#1e3a8a",
        },
        // Semantic verdict colors map to spec v2 §3 severity enum:
        //   NORMAL ↔ verdict-good ; MINOR_DEVIATION ↔ verdict-marginal
        //   SIGNIFICANT_DEVIATION ↔ verdict-moderate ; SEVERE_DEVIATION ↔ verdict-bad
        //   (reserved) ↔ verdict-critical ; INDETERMINATE/UNKNOWN ↔ verdict-unknown
        verdict: {
          good: { bg: "#d1fae5", text: "#065f46", accent: "#10b981" },
          marginal: { bg: "#fef3c7", text: "#92400e", accent: "#f59e0b" },
          moderate: { bg: "#ffedd5", text: "#9a3412", accent: "#f97316" },
          bad: { bg: "#ffe4e6", text: "#9f1239", accent: "#f43f5e" },
          critical: { bg: "#fee2e2", text: "#991b1b", accent: "#ef4444" },
          unknown: { bg: "#f1f5f9", text: "#334155", accent: "#94a3b8" },
        },
      },
      boxShadow: {
        card: "0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)",
      },
    },
  },
  plugins: [],
};
