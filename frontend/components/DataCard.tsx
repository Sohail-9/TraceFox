"use client";

import clsx from "clsx";
import { ReactNode } from "react";
import tokens from "@/theme-tokens";
import { GlassCard } from "@/components/ui/glass-card";

type DataCardProps = {
  title: string;
  value: string | number;
  caption?: string;
  icon?: ReactNode;
  className?: string;
  isLoading?: boolean;
  error?: string | null;
};

export function DataCard({
  title,
  value,
  caption,
  icon,
  className,
  isLoading = false,
  error = null
}: DataCardProps) {
  const ariaLabel = `${title} data card${error ? ' with error' : ''}`;

  return (
    <GlassCard
      intensity="low"
      className={clsx(
        "flex flex-col p-5 h-full justify-between transition-transform duration-300 hover:scale-[1.02]",
        className
      )}
    >
      <div
        role="region"
        aria-label={ariaLabel}
        className="flex items-start justify-between gap-4"
      >
        <div className="space-y-2">
          <p
            className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500"
            aria-label={`${title} label`}
          >
            {title}
          </p>

          {isLoading ? (
            <div className="h-8 w-24 animate-pulse rounded bg-white/10" />
          ) : error ? (
            <div className="text-danger text-sm">{error}</div>
          ) : (
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold tracking-tighter text-transparent bg-clip-text bg-gradient-to-br from-white to-slate-400">
                {typeof value === 'number' ? value.toLocaleString() : value}
              </span>
            </div>
          )}
        </div>

        {/* Icon Container with Glow */}
        {!isLoading && icon && (
          <div className="relative group/icon">
            <div className="absolute inset-0 bg-brand-500/20 blur-xl rounded-full opacity-0 group-hover/icon:opacity-100 transition-opacity" />
            <div className="relative h-10 w-10 flex items-center justify-center rounded-xl bg-white/5 border border-white/10 text-brand-400">
              {icon}
            </div>
          </div>
        )}
      </div>

      {/* Caption / Footer */}
      {(caption || isLoading) && (
        <div className="mt-4 pt-4 border-t border-white/5">
          {isLoading ? (
            <div className="h-3 w-2/3 animate-pulse rounded bg-white/5" />
          ) : (
            <p className="text-xs text-slate-500 font-medium">
              {caption}
            </p>
          )}
        </div>
      )}
    </GlassCard>
  );
}

export default DataCard;
