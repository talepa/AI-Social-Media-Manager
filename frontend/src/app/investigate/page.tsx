"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { LoadingScreen } from "@/components/result/LoadingScreen";
import { AnswerView } from "@/components/result/AnswerView";
import { useInvestigationStream } from "@/lib/useInvestigationStream";
import type { DirectorRequest } from "@/lib/investigationTypes";
import { SearchBox } from "@/components/search/SearchBox";

function readCommission(): DirectorRequest | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem("atelier:commission");
    if (!raw) return null;
    return JSON.parse(raw) as DirectorRequest;
  } catch {
    return null;
  }
}

export default function InvestigatePage() {
  const stream = useInvestigationStream();
  const started = useRef(false);
  const [brief] = useState<DirectorRequest | null>(() => readCommission());

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    if (!brief) return;
    void stream.start(brief);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [brief]);

  const done = stream.phase === "complete" && stream.result;
  const failed = stream.phase === "error" || !!stream.error;

  return (
    <div className="flex min-h-screen flex-col">
      <header
        className="flex items-center justify-between border-b px-5 py-4 md:px-8"
        style={{ borderColor: "var(--rule)" }}
      >
        <Link href="/" className="obs-kicker">
          Atelier
        </Link>
        <Link href="/" className="obs-btn" style={{ padding: "0.5rem 0.9rem" }}>
          New search
        </Link>
      </header>

      {!brief && (
        <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-center px-5 py-16">
          <p className="mb-6 text-[var(--graphite)]">Start with a question.</p>
          <SearchBox autofocus />
        </main>
      )}

      {brief && !done && !failed && (
        <LoadingScreen
          question={stream.question || brief.question}
          phase={stream.phase}
          sourceHint={stream.node?.finding_count}
        />
      )}

      {failed && (
        <main className="mx-auto w-full max-w-xl flex-1 px-5 py-16 text-center">
          <p className="obs-kicker mb-3" style={{ color: "var(--error)" }}>
            Something went wrong
          </p>
          <p className="text-[var(--graphite)]">{stream.error || "Search failed."}</p>
          <Link href="/" className="obs-btn mt-8 inline-flex">
            Try again
          </Link>
        </main>
      )}

      {done && stream.result && <AnswerView result={stream.result} />}
    </div>
  );
}
