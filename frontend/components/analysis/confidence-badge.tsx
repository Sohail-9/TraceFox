"use client";

export function ConfidenceBadge({ confidence }: { confidence: number }): JSX.Element {
  const percent = Math.round(confidence * 100);
  let tone = "bg-slate-800 text-slate-200";
  if (confidence >= 0.9) tone = "bg-rose-500/20 text-rose-200";
  else if (confidence >= 0.7) tone = "bg-amber-500/20 text-amber-200";
  else if (confidence >= 0.5) tone = "bg-emerald-500/20 text-emerald-200";

  return (
    <span className={`rounded-full px-2 py-1 text-[11px] font-semibold uppercase tracking-wide ${tone}`}>
      {percent}% confidence
    </span>
  );
}
