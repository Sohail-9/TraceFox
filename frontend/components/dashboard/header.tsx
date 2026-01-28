"use client";

type DashboardHeaderProps = {
  suggestedRepository?: string;
  suggestedPrNumber?: number;
  onAnalyzed?: (prId: string) => void;
};

export function DashboardHeader({ }: DashboardHeaderProps = {}): JSX.Element {
  return (
    <div className="rounded-3xl border border-white/5 bg-slate-900/40 px-8 py-6 shadow-premium backdrop-blur-md">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-indigo-400/80">
            Mission Control
          </p>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">
            Control Center
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <div className="h-2 w-2 animate-pulse rounded-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">System Ready</span>
        </div>
      </div>
    </div>
  );
}
