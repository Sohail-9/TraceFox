import type { Metadata } from "next";
import "./globals.css";

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
      <body className="min-h-screen bg-slate-950 text-slate-100">
        <div className="mx-auto max-w-6xl px-4 py-10">{children}</div>
      </body>
    </html>
  );
}

