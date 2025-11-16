"use client";

import Link from "next/link";

export default function HomePage(): JSX.Element {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-slate-950 px-6 py-16 text-white">
      <div className="max-w-3xl space-y-6 text-center">
        <p className="text-xs uppercase tracking-[0.45em] text-slate-500">
          TraceFox
        </p>
        <h1 className="text-4xl font-semibold md:text-5xl">
          Mission Control for AI Code Reviews
        </h1>
        <p className="text-lg text-slate-400">
          Visualize DeepSeek + Llama analysis, manage findings, and track PR
          health across every repository. Built with Next.js App Router,
          Tailwind, and precision-first UX.
        </p>
        <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          <Link
            href="/login"
            className="inline-flex items-center justify-center rounded-2xl bg-brand-500 px-6 py-3 text-sm font-semibold uppercase tracking-wide text-white transition hover:bg-brand-400"
          >
            Sign In
          </Link>
          <Link
            href="/dashboard"
            className="inline-flex items-center justify-center rounded-2xl border border-slate-700 px-6 py-3 text-sm font-semibold uppercase tracking-wide text-slate-200 transition hover:border-brand-400/60 hover:text-brand-100"
          >
            View Dashboard
          </Link>
        </div>
      </div>
    </main>
  );
}
