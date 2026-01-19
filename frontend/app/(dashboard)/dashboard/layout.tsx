"use client";

import React, { ReactNode, Suspense } from "react";
import {
  ErrorBoundary as LibErrorBoundary,
  FallbackProps,
} from "react-error-boundary";

import { Sidebar } from "@/components/dashboard/sidebar";
import { TopNav } from "@/components/TopNav";
import { LoadingSpinner } from "@/components/common/loading-spinner";

/* ---------- Type Fix Wrapper ---------- */
const ErrorBoundary = LibErrorBoundary as unknown as React.ComponentType<{
  children: React.ReactNode;
  FallbackComponent: React.ComponentType<FallbackProps>;
}>;

/* ---------- Error UI ---------- */
function ErrorFallback({ error }: FallbackProps) {
  return (
    <div role="alert" className="p-8 text-danger">
      <h2 className="text-xl font-bold">Something went wrong:</h2>
      <p className="mt-2 text-sm">
        {error instanceof Error ? error.message : "Unknown error"}
      </p>
    </div>
  );
}

/* ---------- Layout ---------- */
export default function DashboardLayout({
  children,
}: {
  children: ReactNode;
}): JSX.Element {
  return (
    <div className="flex min-h-screen bg-panel text-ui">

      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 
        focus:z-50 focus:rounded-lg bg-brand px-4 py-2 text-sm 
        font-medium text-white shadow-lg transition 
        focus:ring-2 focus:ring-brand/80 focus:ring-offset-2"
      >
        Skip to main content
      </a>

      <Sidebar />

      <main
        className="flex flex-1 flex-col border-l border-ui/60 bg-panel/70"
        tabIndex={-1}
      >
        <TopNav />

        {/* FIXED ERROR BOUNDARY */}
        <ErrorBoundary FallbackComponent={ErrorFallback}>
          <Suspense
            fallback={
              <div className="flex flex-1 items-center justify-center">
                <LoadingSpinner className="h-12 w-12 text-brand" />
              </div>
            }
          >
            <section
              id="main-content"
              aria-label="Main content"
              className="flex-1 overflow-y-auto px-8 pb-10"
            >
              {children}
            </section>
          </Suspense>
        </ErrorBoundary>

      </main>
    </div>
  );
}
