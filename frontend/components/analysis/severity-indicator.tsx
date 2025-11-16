"use client";

const TONES: Record<string, string> = {
  high: "bg-rose-500/20 text-rose-200",
  medium: "bg-amber-500/20 text-amber-200",
  low: "bg-emerald-500/20 text-emerald-200",
};

export function SeverityIndicator({ severity }: { severity: string }): JSX.Element {
  const tone = TONES[severity?.toLowerCase()] ?? TONES.low;
  return (
    <span className={`rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${tone}`}>
      {severity}
    </span>
  );
}
