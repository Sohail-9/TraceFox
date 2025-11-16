"use client";

export function LoadingSpinner({ label }: { label?: string }): JSX.Element {
  return (
    <div className="flex items-center gap-2 text-slate-400">
      <span className="h-3 w-3 animate-spin rounded-full border-2 border-slate-600 border-t-transparent" />
      <span className="text-xs uppercase tracking-[0.3em]">{label ?? "Loading"}</span>
    </div>
  );
}
