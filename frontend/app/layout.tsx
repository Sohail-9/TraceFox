import type { Metadata } from "next";
import clsx from "clsx";
import { Inter, JetBrains_Mono } from "next/font/google";

import { Providers } from "@/components/Providers";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "TraceFox - AI-Powered Code Review",
  description:
    "Next.js frontend for the TraceFox DeepSeek + Llama analysis platform.",
  keywords: ["TraceFox", "code review", "DeepSeek", "Llama", "GitHub"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}): JSX.Element {
  return (
    <html lang="en">
      <body
        className={clsx(
          inter.className,
          mono.variable,
          "min-h-screen bg-slate-950 text-slate-100 antialiased"
        )}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
