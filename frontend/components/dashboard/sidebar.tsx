"use client";

import clsx from "clsx";
import Link from "next/link";
import { usePathname } from "next/navigation";
import React from "react";

const NAV_ITEMS = [
  { label: "Overview", href: "/dashboard", icon: "🏠" },
  { label: "Pull Requests", href: "/dashboard/pull-requests", icon: "git-pull-request" },
  { label: "Analytics", href: "/dashboard/analytics", icon: "bar-chart-2" },
  { label: "Repositories", href: "/dashboard/repositories", icon: "database" },
  { label: "Settings", href: "/dashboard/settings", icon: "settings" },
];

export function Sidebar(): JSX.Element {
  const pathname = usePathname();

  return (
    <aside className="fixed left-4 top-4 bottom-4 w-64 z-50 flex flex-col">
      {/* Glass Container */}
      <div className="flex-1 flex flex-col rounded-3xl bg-glass border border-white/10 backdrop-blur-xl shadow-2xl overflow-hidden relative">

        {/* Deep Space Gradient Overlay */}
        <div className="absolute inset-0 bg-gradient-to-b from-brand-500/5 to-transparent pointer-events-none" />

        {/* Brand Header */}
        <div className="p-8 relative z-10">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-brand-400 to-brand-600 shadow-lg shadow-brand-500/20 flex items-center justify-center text-white text-xl font-bold">
              TF
            </div>
            <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400 tracking-tight">
              TraceFox
            </span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-6 space-y-2 relative z-10">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  "flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 group",
                  isActive
                    ? "bg-brand-500/10 text-brand-400 border border-brand-500/20 shadow-lg shadow-brand-500/5"
                    : "text-slate-400 hover:text-slate-100 hover:bg-white/5 border border-transparent"
                )}
              >
                {/* Icon Placeholder (Lucide icons recommended for prod) */}
                <span className={clsx(
                  "p-1 rounded-md transition-colors",
                  isActive ? "bg-brand-500/20" : "bg-white/5 group-hover:bg-white/10"
                )}>
                  {/* Simplistic SVG Icons for Demo */}
                  {item.icon === "🏠" && <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" /></svg>}
                  {item.icon === "git-pull-request" && <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" /></svg>}
                  {item.icon === "bar-chart-2" && <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>}
                  {item.icon === "database" && <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" /></svg>}
                  {item.icon === "settings" && <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>}
                </span>

                <span className="font-medium tracking-wide text-sm">{item.label}</span>

                {isActive && (
                  <div className="absolute right-3 w-1.5 h-1.5 rounded-full bg-brand-400 shadow-[0_0_10px_rgba(129,140,248,0.8)]" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* User Profile Snippet */}
        <div className="p-4 mt-auto relative z-10">
          <button className="w-full flex items-center gap-3 p-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/5 transition-colors">
            <div className="h-8 w-8 rounded-full bg-gradient-to-r from-purple-500 to-indigo-500" />
            <div className="flex-1 text-left">
              <div className="text-xs font-bold text-slate-200">User</div>
              <div className="text-[10px] text-slate-500">Pro Plan</div>
            </div>
          </button>
        </div>

      </div>
    </aside>
  );
}
