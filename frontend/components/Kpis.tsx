"use client";

type KpiProps = {
  metrics: {
    label: string;
    value: string | number;
    caption?: string;
  }[];
};

export function KPIGrid({ metrics }: KpiProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {metrics.map((metric) => (
        <div
          key={metric.label}
          className="rounded-xl border border-slate-700 bg-slate-900/50 p-4 shadow-inner shadow-slate-950/40"
        >
          <p className="text-xs uppercase tracking-wide text-slate-400">{metric.label}</p>
          <p className="mt-2 text-2xl font-semibold text-slate-50">{metric.value}</p>
          {metric.caption ? (
            <p className="mt-1 text-xs text-slate-400">{metric.caption}</p>
          ) : null}
        </div>
      ))}
    </div>
  );
}

