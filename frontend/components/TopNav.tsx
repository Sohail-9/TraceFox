"use client";

import { usePathname } from "next/navigation";
import React from "react";

export function TopNav(): JSX.Element {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);

  return (
    <header className="sticky top-0 z-40 px-8 py-4">
      <div className="flex items-center justify-between rounded-2xl bg-glass border border-white/5 backdrop-blur-md px-6 py-3 shadow-lg">
        {/* Breadcrumbs */}
        <div className="flex items-center gap-2 text-sm font-medium">
          {segments.map((segment, index) => (
            <React.Fragment key={segment}>
              {index > 0 && <span className="text-slate-600">/</span>}
              <span
                className={
                  index === segments.length - 1
                    ? "text-brand-400 capitalize"
                    : "text-slate-400 capitalize"
                }
              >
                {segment.replace("-", " ")}
              </span>
            </React.Fragment>
          ))}
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-4">
          <button className="text-xs font-bold uppercase tracking-wider text-slate-500 hover:text-slate-300 transition-colors">
            Feedback
          </button>
          <div className="h-4 w-px bg-white/10" />
          <button className="text-xs font-bold uppercase tracking-wider text-brand-400 hover:text-brand-300 transition-colors">
            Docs
          </button>
        </div>
      </div>
    </header>
  );
}
