"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/dashboard/pull-requests", label: "Pull Requests" },
  { href: "/dashboard/analytics", label: "Analytics" },
];

export function TopNav(): JSX.Element {
  const pathname = usePathname();
  return (
    <nav className="sticky top-0 z-40 mb-8 flex items-center justify-between rounded-2xl border border-slate-800/70 bg-slate-950/80 px-5 py-3 backdrop-blur">
      <div>
        <p className="text-xs uppercase tracking-[0.35em] text-slate-500">
          TraceFox
        </p>
        <p className="font-mono text-[11px] uppercase tracking-[0.3em] text-slate-400">
          DeepSeek · Llama · Neo4j · RabbitMQ
        </p>
      </div>
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={
                "rounded-full border px-3 py-1 transition " +
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
    </nav>
  );
}
