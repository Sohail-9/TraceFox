// Centralized design tokens (JS export) to keep colors and spacing consistent
export const tokens = {
  colors: {
    brand: "#6366f1", // Indigo 500
    brandLight: "#818cf8", // Indigo 400
    bg: "#030014", // Deep Void
    panel: "#0f172a", // Nebula
    panelBorder: "rgba(255, 255, 255, 0.08)", // Glass Border
    muted: "#64748b", // Slate 500
    text: "#f8fafc", // Slate 50
    textMuted: "#94a3b8", // Slate 400
    glass: "rgba(255, 255, 255, 0.03)",
    glassStrong: "rgba(255, 255, 255, 0.08)",
    severity: {
      high: "#f43f5e", // Rose 500
      medium: "#f59e0b", // Amber 500
      low: "#10b981", // Emerald 500
    },
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
  },
  typography: {
    mono: "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, monospace",
    ui: "'Inter', ui-sans-serif, system-ui, -apple-system, 'Segoe UI'",
  },
  chartColors: ["#6366f1", "#06b6d4", "#a855f7", "#10b981"],
};

export default tokens;
