"use client";

import { ReactNode } from "react";

import { Sidebar } from "@/components/dashboard/sidebar";
import { TopNav } from "@/components/TopNav";

export default function DashboardLayout({
  children,
}: {
  children: ReactNode;
}): JSX.Element {
  return (
    <div className="flex min-h-screen bg-slate-950 text-white">
      <Sidebar />
      <div className="flex flex-1 flex-col border-l border-slate-900 bg-slate-950/70">
        <TopNav />
        <div className="flex-1 overflow-y-auto px-8 pb-10">{children}</div>
      </div>
    </div>
  );
}
