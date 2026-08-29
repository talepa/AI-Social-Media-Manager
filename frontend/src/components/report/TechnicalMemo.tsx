"use client";

import type { InvestigationRunResponse } from "@/lib/investigationTypes";

export function TechnicalMemo({
  result,
  onCite,
}: {
  result: InvestigationRunResponse;
  onCite?: (id: string) => void;
}) {
  const report = result.report;
  const verification = result.verification;
  if (!report) {
    return (
      <p className="obs-mono p-6 text-[0.7rem] text-[var(--muted)]">No report</p>
    );
  }

  return (
    <article className="memo px-5 py-10 md:px-8 md:py-14">
      <p className="obs-kicker">Atelier</p>
      <h1 className="obs-display mt-2 text-3xl md:text-4xl">
        Technical Intelligence Report
      </h1>
      <p className="obs-mono mt-3 text-[0.7rem] tracking-[0.12em] text-[var(--muted)]">
        RUN {result.run_id.slice(0, 8).toUpperCase()}
      </p>

      <hr className="obs-rule my-6" />

      <p className="obs-kicker">Question</p>
      <p className="mt-2 text-lg" style={{ fontFamily: "var(--serif)" }}>
        {result.plan.objective}
      </p>

      <div className="obs-mono mt-5 flex flex-wrap gap-5 text-[0.65rem] tracking-[0.1em] text-[var(--muted)]">
        <span>EVIDENCE {result.sources.length} SOURCES</span>
        <span>CLAIMS {result.evidence?.claims.length ?? 0}</span>
        <span>
          VALIDATION{" "}
          {verification?.passed ? (
            <span style={{ color: "var(--success)" }}>PASSED</span>
          ) : (
            <span style={{ color: "var(--error)" }}>FAILED</span>
          )}
        </span>
      </div>

      <hr className="obs-rule my-8" />

      <h2 className="obs-display text-2xl">Executive conclusion</h2>
      <p className="mt-4">{report.executive_summary || report.headline}</p>

      {report.sections.map((sec) => (
        <section key={sec.title} className="mt-10">
          <h2 className="obs-display text-2xl">{sec.title}</h2>
          <p className="mt-4 whitespace-pre-wrap">{sec.body}</p>
          {(sec.claim_ids.length > 0 || sec.source_ids.length > 0) && (
            <div className="mt-3 flex flex-wrap gap-2">
              {[...sec.claim_ids, ...sec.source_ids].map((id) => (
                <button
                  key={id}
                  type="button"
                  className="cite-chip"
                  onClick={() => onCite?.(id)}
                >
                  {id}
                </button>
              ))}
            </div>
          )}
        </section>
      ))}

      <hr className="obs-rule my-10" />
      <h2 className="obs-display text-2xl">Sources</h2>
      <ol className="mt-4 space-y-3">
        {result.sources.map((s) => (
          <li key={s.id} className="border-b pb-3" style={{ borderColor: "var(--rule)" }}>
            <button
              type="button"
              className="cite-chip mb-1"
              onClick={() => onCite?.(s.id)}
            >
              {s.id}
            </button>
            <div className="text-sm">{s.title}</div>
            <a
              href={s.url}
              target="_blank"
              rel="noreferrer"
              className="obs-mono text-[0.65rem] text-[var(--signal)] break-all"
            >
              {s.url}
            </a>
          </li>
        ))}
      </ol>
    </article>
  );
}
