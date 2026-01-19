"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const MENU_ITEMS = [
  { href: "/dashboard", label: "Overview", icon: "📊" },
  { href: "/dashboard/pull-requests", label: "Pull Requests", icon: "🔍" },
  { href: "/dashboard/analytics", label: "Analytics", icon: "📈" },
  { href: "/dashboard/settings", label: "Settings", icon: "⚙️" },
];

export function Sidebar(): JSX.Element {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={`hidden lg:flex flex-col transition-all duration-200 ${
        collapsed ? "w-20" : "w-64"
      } border-r border-ui bg-panel p-4 text-sm`}
    >
      <div className="mb-6 flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.45em] text-muted">TraceFox</p>
          {!collapsed ? (
            <p className="text-lg font-semibold text-white">Mission Control</p>
          ) : null}
        </div>
        <button
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          onClick={() => setCollapsed((s) => !s)}
          className="rounded-full border border-ui px-2 py-1 text-xs text-muted"
        >
          {collapsed ? "›" : "‹"}
        </button>
      </div>

      <nav className="flex-1 space-y-2">
        {MENU_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-2xl px-3 py-2 transition ${
                  isActive
                    ? "bg-brand-500/20 text-ui"
                    : "text-muted hover:bg-panel/90 hover:text-ui"
                }`}
            >
              <span className="text-lg">{item.icon}</span>
              {!collapsed ? <span>{item.label}</span> : null}
            </Link>
          );
        })}
      </nav>

      <div className="mt-6 space-y-3 text-xs text-muted">
        {!collapsed ? (
          <p>AI-powered reviews · Orchestration · Graph insights</p>
        ) : null}
        <Link
          href="/login"
          className={`inline-flex w-full items-center justify-center rounded-2xl border border-ui px-3 py-2 text-sm font-semibold text-ui transition ${
            collapsed ? "px-2 py-1 text-xs" : ""
          }`}
        >
          {!collapsed ? "Sign Out" : "⎋"}
        </Link>
      </div>
    </aside>
  );
}
