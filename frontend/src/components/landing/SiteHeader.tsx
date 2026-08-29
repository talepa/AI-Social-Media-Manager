"use client";

import Link from "next/link";

export function SiteHeader({ compact = false }: { compact?: boolean }) {
  return (
    <header
      className="flex items-center justify-between border-b px-5 py-4 md:px-8"
      style={{ borderColor: "var(--rule)" }}
    >
      <Link href="/" className="flex items-baseline gap-3">
        <span className="obs-kicker">Atelier / 01</span>
        {!compact && (
          <span className="obs-display text-lg md:text-xl">Technical Intelligence</span>
        )}
      </Link>
      <nav className="flex items-center gap-4">
        <Link href="/commission" className="obs-kicker hover:text-[var(--signal)]">
          Commission
        </Link>
        <Link href="/commission" className="obs-btn">
          Start investigation
        </Link>
      </nav>
    </header>
  );
}
