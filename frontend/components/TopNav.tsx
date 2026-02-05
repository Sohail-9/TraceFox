"use client";

import { usePathname, useRouter } from "next/navigation";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import { clearSession, loadUser, SessionUser } from "@/lib/session";

function UserMenu(): JSX.Element | null {
  const router = useRouter();
  const [user, setUser] = useState<SessionUser | null>(null);

  useEffect(() => {
    setUser(loadUser());
  }, []);

  const handleSignOut = () => {
    clearSession();
    router.replace("/login");
  };

  if (!user) {
    return null;
  }

  return (
    <div className="flex items-center gap-3 pl-3 border-l border-white/10">
      <div className="text-right hidden sm:block">
        <p className="text-xs font-bold text-slate-200">{user.name || user.login}</p>
      </div>
      {user.avatar_url ? (
        <img
          src={user.avatar_url}
          alt={user.login}
          className="h-8 w-8 rounded-full border border-white/10 shadow-sm"
        />
      ) : (
        <div className="h-8 w-8 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-xs font-bold text-indigo-300">
          {user.login.slice(0, 2).toUpperCase()}
        </div>
      )}
      <button
        onClick={handleSignOut}
        className="ml-2 text-[10px] font-bold uppercase tracking-widest text-rose-400 hover:text-rose-300 transition-colors"
      >
        Sign Out
      </button>
    </div>
  );
}

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

          <UserMenu />
        </div>
      </div>
    </header>
  );
}
