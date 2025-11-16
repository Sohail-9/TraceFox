"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const MENU_ITEMS = [
  { href: "/dashboard", label: "Overview", icon: "📊" },
  { href: "/dashboard/pull-requests", label: "Pull Requests", icon: "🔍" },
  { href: "/dashboard/analytics", label: "Analytics", icon: "📈" },
  { href: "/dashboard/settings", label: "Settings", icon: "⚙️" },
];

export function Sidebar(): JSX.Element {
  const pathname = usePathname();
  return (
    <aside className="hidden w-64 flex-col border-r border-slate-900 bg-slate-950/90 p-6 text-sm lg:flex">
      <div className="mb-8">
        <p className="text-xs uppercase tracking-[0.45em] text-slate-500">TraceFox</p>
        <p className="text-lg font-semibold text-white">Mission Control</p>
        <p className="text-xs text-slate-500">DeepSeek + Llama pipeline</p>
      </div>
      <nav className="flex-1 space-y-2">
        {MENU_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-2xl px-4 py-2 transition ${
                isActive
                  ? "bg-brand-500/20 text-white"
                  : "text-slate-400 hover:bg-slate-900 hover:text-white"
              }`}
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="mt-8 space-y-3 text-xs text-slate-500">
        <p>DeepSeek via Loa Krutrim · Llama 3 pipelines · Graph insights</p>
        <Link
          href="/login"
          className="inline-flex w-full items-center justify-center rounded-2xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:border-rose-400 hover:text-rose-200"
        >
          Sign Out
        </Link>
      </div>
    </aside>
  );
}
