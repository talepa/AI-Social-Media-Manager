"use client";

import Link from "next/link";
import { SearchBox } from "@/components/search/SearchBox";

/** Friendly alias of home search — keeps old /commission links working. */
export default function CommissionPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex items-center justify-between px-5 py-5 md:px-8">
        <Link href="/" className="obs-kicker">
          Atelier
        </Link>
      </header>
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-center px-5 py-16">
        <h1 className="obs-display mb-8 text-center text-3xl">New search</h1>
        <SearchBox autofocus />
      </main>
    </div>
  );
}
