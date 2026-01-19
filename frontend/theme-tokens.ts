// Centralized design tokens (JS export) to keep colors and spacing consistent
export const tokens = {
  colors: {
    brand: "#426af6",
    bg: "#030712",
    panel: "#0b1220",
    muted: "#94a3b8",
    text: "#e6eef8",
    glass: "rgba(255,255,255,0.03)",
    severity: {
      high: "#fb7185",
      medium: "#f59e0b",
      low: "#10b981",
    },
  },
  spacing: {
    sm: 8,
    md: 16,
    lg: 24,
  },
  typography: {
    mono: "JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, Monaco, monospace",
    ui: "Inter, ui-sans-serif, system-ui, -apple-system, \"Segoe UI\"",
  },
  chartColors: ["#7c3aed", "#60a5fa", "#34d399", "#f97316"],
};

export default tokens;
