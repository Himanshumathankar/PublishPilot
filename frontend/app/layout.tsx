import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "PublishPilot",
  description: "Review, optimize, and publish articles across WordPress websites",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <header className="border-b border-[var(--line)] bg-white">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <Link href="/dashboard" className="text-lg font-bold tracking-tight">PublishPilot</Link>
            <nav className="flex gap-6 text-sm font-medium text-[var(--muted)]" aria-label="Primary navigation">
              <Link href="/dashboard" className="hover:text-[var(--brand)]">Dashboard</Link>
              <Link href="/articles/new" className="hover:text-[var(--brand)]">New article</Link>
              <Link href="/articles/history" className="hover:text-[var(--brand)]">History</Link>
              <Link href="/settings" className="hover:text-[var(--brand)]">Settings</Link>
            </nav>
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
