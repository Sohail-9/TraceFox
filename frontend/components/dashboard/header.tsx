"use client";

export function DashboardHeader(): JSX.Element {
  return (
    <div className="rounded-3xl border border-ui/40 bg-glass px-6 py-5 shadow-xl shadow-soft">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-ui">Control Center</h1>
        </div>
      </div>
    </div>
  );
}
