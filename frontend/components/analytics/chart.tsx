"use client";

export function AnalyticsChart(): JSX.Element {
  return (
    <div className="rounded-3xl border border-ui bg-panel p-6 text-center text-sm text-muted">
      <p>Charts integrate with your preferred analytics provider.</p>
      <p className="text-xs text-muted">
        Hook this component to Prometheus, DataDog, or the TraceFox analytics API.
      </p>
    </div>
  );
}
