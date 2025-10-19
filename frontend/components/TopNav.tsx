"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Control Center" },
  { href: "/docs", label: "Docs" },
  { href: "/status", label: "Status" },
];

export function TopNav(): JSX.Element {
  const pathname = usePathname();

  return (
    <nav className="sticky top-0 z-40 mb-8 flex items-center justify-between rounded-2xl border border-slate-800/70 bg-slate-950/70 px-4 py-3 backdrop-blur">
      <span className="text-xs uppercase tracking-[0.35em] text-slate-400">TraceFox</span>
      <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-wide text-slate-300">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={
                "rounded-full border px-3 py-1 transition " +
                (isActive
                  ? "border-brand-500/60 bg-brand-500/10 text-white"
                  : "border-slate-700/70 bg-transparent hover:border-brand-400/40 hover:text-brand-200")
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
