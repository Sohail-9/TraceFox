"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import RepoPicker from "@/components/RepoPicker";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/dashboard/pull-requests", label: "Pull Requests" },
  { href: "/dashboard/analytics", label: "Analytics" },
];

export function TopNav(): JSX.Element {
  const pathname = usePathname();
  return (
    <nav 
      aria-label="Main navigation"
      className="sticky top-0 z-40 mb-8 flex items-center justify-between rounded-2xl border border-ui bg-panel px-4 py-2 backdrop-blur"
    >
      <div>
        <p className="text-xs uppercase tracking-[0.35em] text-slate-500">
          TraceFox
        </p>
        <p className="font-mono text-[11px] uppercase tracking-[0.3em] text-slate-400">
          TraceFox Control Center
        </p>
      </div>
        <div className="flex items-center gap-4 text-xs font-semibold uppercase tracking-wide">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={isActive ? "page" : undefined}
              className={
                "rounded-full border px-3 py-1 transition " +
                "focus:outline-none focus:ring-2 focus:ring-brand/50 " +
                (isActive
                  ? "border-brand-400/70 bg-brand-500/20 text-white"
                  : "border-slate-700/60 text-slate-400 hover:border-brand-400/40 hover:text-brand-100")
              }
            >
              {item.label}
            </Link>
          );
        })}
      </div>
        <div className="flex items-center gap-3">
          <div className="hidden md:block">
              <input
                aria-label="Search"
                placeholder="Search findings, pull requests, files..."
                className="rounded-md border border-ui/40 bg-glass px-3 py-2 text-sm text-ui placeholder:text-muted focus:ring-2 focus:ring-brand/50"
              />
          </div>
          <RepoPicker />
        </div>
    </nav>
  );
}
