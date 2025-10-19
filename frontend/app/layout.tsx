import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import clsx from "clsx";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });
const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "DevGuardian Control Center",
  description: "Live outlook of DevGuardian AI pipeline activity.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={clsx(
          inter.className,
          mono.variable,
          "min-h-screen bg-slate-950 text-slate-100 antialiased"
        )}
      >
        <div className="relative overflow-hidden">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(99,102,241,0.28),_transparent_55%),radial-gradient(circle_at_bottom,_rgba(168,85,247,0.18),_transparent_60%)]" />
          <div className="relative z-10 mx-auto flex min-h-screen max-w-6xl flex-col px-6 pb-10 pt-8 md:px-10">
            <header className="mb-10 flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
              <div>
                <div className="inline-flex items-center gap-2 rounded-full border border-brand-500/40 bg-brand-500/10 px-4 py-1 text-xs uppercase tracking-wider text-brand-100 shadow shadow-brand-900/40">
                  DevGuardian
                  <span className="text-brand-200">Control Center</span>
                </div>
                <h1 className="mt-4 text-3xl font-semibold text-white md:text-4xl">
                  Your AI-powered SDLC command room
                </h1>
                <p className="mt-2 max-w-2xl text-sm text-slate-300">
                  Monitor commit intelligence, automated testing, debugging RCA, and production
                  telemetry with real-time insights orchestrated by Krutrim DeepSeek R1.
                </p>
              </div>
              <div className="flex items-center gap-3">
                <a
                  href="https://devguardian.ai"
                  target="_blank"
                  className="rounded-full border border-slate-700/70 bg-slate-900/60 px-4 py-2 text-xs uppercase tracking-wide text-slate-300 transition hover:border-brand-400/60 hover:text-brand-100"
                >
                  View Docs
                </a>
                <a
                  href="https://status.devguardian.ai"
                  target="_blank"
                  className="rounded-full border border-brand-500/70 bg-brand-500/15 px-4 py-2 text-xs uppercase tracking-wide text-brand-100 shadow-md shadow-brand-900/40 transition hover:bg-brand-500/25"
                >
                  Platform Status
                </a>
              </div>
            </header>
            <main className="flex-1">{children}</main>
            <footer className="mt-12 flex flex-col gap-2 border-t border-slate-800/60 pt-6 text-xs text-slate-500 md:flex-row md:items-center md:justify-between">
              <p>© {new Date().getFullYear()} DevGuardian Labs. All rights reserved.</p>
              <p className="font-mono text-[11px] uppercase tracking-wider text-slate-600">
                Powered by Krutrim DeepSeek R1 • Intelligent SDLC automation
              </p>
            </footer>
          </div>
        </div>
      </body>
    </html>
  );
}

