"use client";

import { useMemo } from "react";
import type {
  InvestigationRunResponse,
  SourceRecord,
} from "@/lib/investigationTypes";

function stripRawIds(text: string): string {
  return text
    .replace(
      /\s*\((?:WEB|PAPER|GH|NEWS|DOC|CLAIM|F)-\d{3,}(?:\s*,\s*(?:WEB|PAPER|GH|NEWS|DOC|CLAIM|F)-\d{3,})*\)/g,
      "",
    )
    .replace(
      /\s*\[(?:WEB|PAPER|GH|NEWS|DOC|CLAIM|F)-\d{3,}(?:\s*,\s*(?:WEB|PAPER|GH|NEWS|DOC|CLAIM|F)-\d{3,})*\]/g,
      "",
    )
    .replace(/\[\[[^\]]*\]\]/g, "")
    .trim();
}

export function AnswerView({ result }: { result: InvestigationRunResponse }) {
  const report = result.report;
  const allSources = useMemo(() => result.sources || [], [result.sources]);

  const shortText = stripRawIds(
    report?.sections.find((s) => s.title.toLowerCase() === "short answer")?.body ||
      report?.executive_summary ||
      "",
  );

  const sources: SourceRecord[] = useMemo(() => {
    const citedIds = report?.cited_source_ids?.length
      ? report.cited_source_ids
      : report?.sections.find((s) => s.title.toLowerCase() === "sources")
          ?.source_ids || [];
    const byId = new Map(allSources.map((s) => [s.id, s]));
    const ordered: SourceRecord[] = [];
    for (const id of citedIds) {
      const s = byId.get(id);
      if (s) ordered.push(s);
    }
    return ordered;
  }, [allSources, report]);

  const thin = !shortText && sources.length === 0;

  return (
    <div className="mx-auto w-full max-w-2xl px-5 py-10 md:px-8 md:py-14">
      <nav
        className="mb-8 flex gap-2"
      >
        <a
          href="#answer"
          className="obs-mono rounded-full border px-3 py-1.5 text-[0.7rem]"
          style={{ borderColor: "var(--rule)", background: "var(--surface)" }}
        >
          Answer
        </a>
        <a
          href="#sources"
          className="obs-mono rounded-full border px-3 py-1.5 text-[0.7rem]"
          style={{ borderColor: "var(--rule)", background: "var(--surface)" }}
        >
          Sources ({sources.length})
        </a>
      </nav>

      <p className="obs-kicker">Answer</p>
      <h1 id="answer" className="obs-display mt-2 scroll-mt-8 text-3xl md:text-4xl">
        {result.plan?.objective || report?.headline || "Result"}
      </h1>

      {thin ? (
        <p className="mt-6 text-[var(--error)]">
          We couldn&apos;t find clean evidence for this. Try rephrasing the
          question.
        </p>
      ) : (
        <p
          className="mt-6 text-lg leading-relaxed text-[var(--graphite)]"
          style={{ fontFamily: "var(--serif)" }}
        >
          {shortText || "See the sources below for context."}
        </p>
      )}

      <hr className="obs-rule my-10" />

      <section id="sources" className="scroll-mt-8">
        <div className="mb-4 flex items-end justify-between">
          <h2 className="obs-display text-2xl">Sources</h2>
          <span className="obs-mono text-[0.65rem] text-[var(--muted)]">
            {sources.length} used
          </span>
        </div>
        {sources.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">No sources to show.</p>
        ) : (
          <ol className="space-y-4">
            {sources.map((s, i) => (
              <li
                key={s.id}
                className="border-b pb-4"
                style={{ borderColor: "var(--rule)" }}
              >
                <div className="obs-mono text-[0.65rem] text-[var(--muted)]">
                  [{i + 1}] · {s.type}
                </div>
                <a
                  href={s.url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-1 block text-base hover:text-[var(--signal)]"
                  style={{ fontFamily: "var(--serif)" }}
                >
                  {s.title || s.url}
                </a>
                <a
                  href={s.url}
                  target="_blank"
                  rel="noreferrer"
                  className="obs-mono mt-1 block break-all text-[0.65rem] text-[var(--signal)]"
                >
                  {s.url}
                </a>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}
