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
          className="group relative overflow-hidden rounded-2xl border border-ui bg-glass p-5 shadow-soft transition hover:-translate-y-0.5 hover:border-brand-400/60"
        >
          <div className="absolute -left-10 top-1/2 h-24 w-24 -translate-y-1/2 rotate-12 rounded-full bg-brand-500/10 opacity-0 blur-2xl transition group-hover:opacity-100" />
          <p className="text-xs uppercase tracking-wide text-slate-400">{metric.label}</p>
          <p className="mt-3 text-3xl font-semibold text-ui">{metric.value}</p>
          {metric.caption ? (
            <p className="mt-2 text-xs text-muted">{metric.caption}</p>
          ) : null}
        </div>
      ))}
    </div>
  );
}
