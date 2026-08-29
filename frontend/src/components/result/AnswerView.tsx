"use client";

import { useMemo } from "react";
import type {
  InvestigationRunResponse,
  SourceRecord,
} from "@/lib/investigationTypes";

const REF_TAIL = /\[\[([^\]]*)\]\]\s*$/;

function parseDetailBlocks(body: string): { text: string; refIds: string[] }[] {
  return body
    .split(/\n\n+/)
    .map((block) => block.trim())
    .filter(Boolean)
    .map((block) => {
      const m = block.match(REF_TAIL);
      if (!m) return { text: block, refIds: [] as string[] };
      const text = block.slice(0, m.index).trim();
      const refIds = m[1]
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      return { text, refIds };
    });
}

function stripRawIds(text: string): string {
  return text
    .replace(/\s*\((?:WEB|PAPER|GH|NEWS|DOC|CLAIM|F)-\d{3,}(?:\s*,\s*(?:WEB|PAPER|GH|NEWS|DOC|CLAIM|F)-\d{3,})*\)/g, "")
    .replace(/\s*\[(?:WEB|PAPER|GH|NEWS|DOC|CLAIM|F)-\d{3,}(?:\s*,\s*(?:WEB|PAPER|GH|NEWS|DOC|CLAIM|F)-\d{3,})*\]/g, "")
    .trim();
}

export function AnswerView({ result }: { result: InvestigationRunResponse }) {
  const sources = useMemo(() => result.sources || [], [result.sources]);
  const report = result.report;

  const shortSection =
    report?.sections.find((s) => s.title.toLowerCase() === "short answer") ||
    null;
  const detailsSection =
    report?.sections.find((s) => s.title.toLowerCase() === "details") ||
    report?.sections.find((s) => s.title.toLowerCase() === "answer") ||
    null;

  const { footnoteOrder, idToNum } = useMemo(() => {
    const order: string[] = [];
    const seen = new Set<string>();
    const push = (id: string) => {
      if (!id || seen.has(id)) return;
      seen.add(id);
      order.push(id);
    };
    for (const c of result.evidence?.claims || []) {
      for (const id of c.supporting_source_ids) push(id);
    }
    for (const id of report?.cited_source_ids || []) push(id);
    for (const s of sources) push(s.id);
    const map = new Map<string, number>();
    order.forEach((id, i) => map.set(id, i + 1));
    return { footnoteOrder: order, idToNum: map };
  }, [result.evidence, report?.cited_source_ids, sources]);

  const sourceById = useMemo(() => {
    const m = new Map<string, SourceRecord>();
    for (const s of sources) m.set(s.id, s);
    return m;
  }, [sources]);

  const orderedSources = footnoteOrder
    .map((id) => sourceById.get(id))
    .filter((s): s is SourceRecord => !!s);

  const shortText = stripRawIds(
    shortSection?.body || report?.executive_summary || "",
  );
  const detailBlocks = parseDetailBlocks(detailsSection?.body || "").map((b) => ({
    text: stripRawIds(b.text),
    refIds: b.refIds,
  }));

  const thin = !shortText && detailBlocks.length === 0 && orderedSources.length === 0;

  return (
    <div className="mx-auto w-full max-w-5xl px-5 py-8 md:px-8 md:py-10">
      {/* Jump nav — short answer, details, sources in one go */}
      <nav
        className="sticky top-0 z-20 -mx-5 mb-8 flex gap-1 overflow-x-auto border-b px-5 py-3 md:-mx-8 md:px-8"
        style={{
          borderColor: "var(--rule)",
          background: "color-mix(in srgb, var(--bg) 92%, white)",
          backdropFilter: "blur(8px)",
        }}
      >
        {[
          ["#short-answer", "Short answer"],
          ["#details", "Details"],
          ["#sources", `Sources (${orderedSources.length})`],
        ].map(([href, label]) => (
          <a
            key={href}
            href={href}
            className="obs-mono whitespace-nowrap rounded-full border px-3 py-1.5 text-[0.7rem] tracking-[0.06em] hover:border-[var(--signal)]"
            style={{ borderColor: "var(--rule)", background: "var(--surface)" }}
          >
            {label}
          </a>
        ))}
      </nav>

      <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_17rem]">
        <div>
          <p className="obs-kicker">Answer</p>
          <h1 className="obs-display mt-2 text-3xl md:text-4xl">
            {result.plan?.objective || report?.headline || "Result"}
          </h1>

          {thin ? (
            <p className="mt-6 text-[var(--error)]">
              We couldn&apos;t build a solid answer. Try a clearer question or a
              deeper search.
            </p>
          ) : (
            <>
              <section id="short-answer" className="scroll-mt-24 mt-8">
                <h2 className="obs-display text-2xl">Short answer</h2>
                <p
                  className="mt-4 text-lg leading-relaxed text-[var(--graphite)]"
                  style={{ fontFamily: "var(--serif)" }}
                >
                  {shortText || "See details below."}
                </p>
              </section>

              <section id="details" className="scroll-mt-24 mt-10">
                <h2 className="obs-display text-2xl">Details</h2>
                <div className="mt-4 space-y-5 text-[var(--graphite)] leading-relaxed">
                  {detailBlocks.length === 0 ? (
                    <p className="text-sm text-[var(--muted)]">No further detail.</p>
                  ) : (
                    detailBlocks.map((block, i) => (
                      <p key={i}>
                        {block.text}
                        {block.refIds.map((id) => {
                          const n = idToNum.get(id);
                          if (!n) return null;
                          return (
                            <sup key={id}>
                              <a
                                href={`#ref-${n}`}
                                className="ml-0.5 text-[0.7rem] text-[var(--signal)] no-underline hover:underline"
                                title={sourceById.get(id)?.title || id}
                              >
                                [{n}]
                              </a>
                            </sup>
                          );
                        })}
                      </p>
                    ))
                  )}
                </div>
              </section>

              {/* Sources also inline for mobile / scrollers */}
              <section id="sources" className="scroll-mt-24 mt-12 lg:hidden">
                <SourcesList sources={orderedSources} />
              </section>
            </>
          )}
        </div>

        {/* Desktop: sources always visible beside the answer */}
        <aside className="hidden lg:block">
          <div
            className="sticky top-20 max-h-[calc(100vh-6rem)] overflow-y-auto border p-4"
            style={{ borderColor: "var(--rule)", background: "var(--surface)" }}
            id="sources-panel"
          >
            <SourcesList sources={orderedSources} compact />
          </div>
        </aside>
      </div>
    </div>
  );
}

function SourcesList({
  sources,
  compact = false,
}: {
  sources: SourceRecord[];
  compact?: boolean;
}) {
  return (
    <div>
      <div className="mb-3 flex items-end justify-between gap-2">
        <h2 className={`obs-display ${compact ? "text-lg" : "text-2xl"}`}>Sources</h2>
        <span className="obs-mono text-[0.65rem] text-[var(--muted)]">
          {sources.length}
        </span>
      </div>
      {sources.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">No sources</p>
      ) : (
        <ol className="space-y-3">
          {sources.map((s, i) => (
            <li
              key={s.id}
              id={`ref-${i + 1}`}
              className="scroll-mt-24 border-b pb-3"
              style={{ borderColor: "var(--rule)" }}
            >
              <div className="obs-mono text-[0.65rem] text-[var(--muted)]">
                [{i + 1}] · {s.type}
              </div>
              <a
                href={s.url}
                target="_blank"
                rel="noreferrer"
                className={`mt-0.5 block hover:text-[var(--signal)] ${compact ? "text-sm" : "text-base"}`}
                style={{ fontFamily: "var(--serif)" }}
              >
                {s.title || s.url}
              </a>
              {!compact && s.content && (
                <p className="mt-1 line-clamp-2 text-xs text-[var(--graphite)]">
                  {s.content}
                </p>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
