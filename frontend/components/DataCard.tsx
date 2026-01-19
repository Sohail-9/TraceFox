"use client";

import clsx from "clsx";
import { ReactNode } from "react";
import tokens from "@/theme-tokens";

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
    <div
      role="region"
      aria-label={ariaLabel}
      className={clsx(
        "group relative flex items-start gap-4 rounded-2xl border border-ui bg-glass p-4",
        "transition-all duration-300 ease-out hover:-translate-y-1 hover:shadow-lg",
        "bg-gradient-to-b from-glass/50 to-glass/20 hover:from-glass/70 hover:to-glass/40",
        "focus:ring-2 focus:ring-brand/50 outline-none focus:outline-none",
        "sm:p-6",
        className
      )}
      tabIndex={0}
    >
      {!isLoading && icon ? (
        <div
          className="mt-1 text-2xl"
          style={{ color: tokens.colors.brand }}
          aria-hidden="true"
        >
          {icon}
        </div>
      ) : null}
      
      {isLoading && (
        <div className="mt-1 h-8 w-8 animate-pulse rounded-full bg-ui/20" />
      )}
      <div className="flex-1 space-y-2">
        {isLoading ? (
          <>
            <div className="h-4 w-24 animate-pulse rounded bg-ui/20" />
            <div className="h-8 w-32 animate-pulse rounded bg-ui/20" />
          </>
        ) : error ? (
          <div className="text-danger">
            <p className="text-sm font-medium">Error loading data</p>
            <p className="text-xs">{error}</p>
          </div>
        ) : (
          <>
            <p 
              className="text-xs uppercase tracking-wide text-muted-foreground"
              aria-label={`${title} label`}
            >
              {title}
            </p>
            <p 
              className="mt-1 text-2xl font-semibold text-foreground"
              aria-live="polite"
            >
              {typeof value === 'number' ? value.toLocaleString() : value}
            </p>
            {caption && (
              <p className="mt-1 text-xs text-muted-foreground">
                {caption}
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default DataCard;
