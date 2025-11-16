"use client";

export function AnalyticsChart(): JSX.Element {
  return (
    <div className="rounded-3xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-950 p-6 text-center text-sm text-slate-400">
      <p>Charts integrate with your preferred analytics provider.</p>
      <p className="text-xs text-slate-500">
        Hook this component to Prometheus, DataDog, or the TraceFox analytics API.
      </p>
    </div>
  );
}
