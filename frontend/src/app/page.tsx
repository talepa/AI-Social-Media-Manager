"use client";

import Link from "next/link";
import { SearchBox } from "@/components/search/SearchBox";

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col">
      <header
        className="flex items-center justify-between px-5 py-5 md:px-8"
      >
        <Link href="/" className="obs-kicker">
          Atelier
        </Link>
      </header>

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-center justify-center px-5 pb-20">
        <p className="obs-kicker mb-4">Technical research</p>
        <h1 className="obs-display mb-3 text-center text-4xl md:text-5xl">
          Ask a hard question
        </h1>
        <p className="mb-10 max-w-md text-center text-[var(--graphite)]">
          Get a clear answer with sources — web, papers, and code — in one place.
        </p>
        <SearchBox autofocus />
      </main>
    </div>
  );
}
