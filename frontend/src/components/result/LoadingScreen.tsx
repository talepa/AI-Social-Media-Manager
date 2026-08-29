"use client";

import type { RunPhase } from "@/lib/investigationTypes";

const STEPS: { match: RunPhase[]; label: string; tip: string }[] = [
  {
    match: ["idle", "accepted", "director"],
    label: "Understanding your question",
    tip: "Breaking it into what we need to look up.",
  },
  {
    match: ["specialists"],
    label: "Searching the web, papers, and code",
    tip: "Gathering sources that can actually answer this.",
  },
  {
    match: ["evidence"],
    label: "Sorting what matters",
    tip: "Turning sources into clear points with citations.",
  },
  {
    match: ["synthesis"],
    label: "Writing your answer",
    tip: "Putting it together in a readable report.",
  },
];

export function LoadingScreen({
  question,
  phase,
  sourceHint,
}: {
  question: string;
  phase: RunPhase;
  sourceHint?: number;
}) {
  const activeIdx = Math.max(
    0,
    STEPS.findIndex((s) => s.match.includes(phase)),
  );
  const step = STEPS[activeIdx] || STEPS[0];

  return (
    <div className="mx-auto flex w-full max-w-xl flex-1 flex-col items-center justify-center px-5 py-16 text-center">
      <div className="obs-pulse mb-6" style={{ width: "0.75rem", height: "0.75rem" }} />
      <p className="obs-kicker mb-3">Working on it</p>
      <h1 className="obs-display text-2xl md:text-3xl">{step.label}</h1>
      <p className="mt-3 text-sm text-[var(--graphite)]">{step.tip}</p>

      <blockquote
        className="mt-8 w-full border-l-2 px-4 py-2 text-left text-base"
        style={{ borderColor: "var(--signal)", fontFamily: "var(--serif)" }}
      >
        {question}
      </blockquote>

      <ol className="mt-10 w-full space-y-3 text-left">
        {STEPS.map((s, i) => {
          const done = i < activeIdx || phase === "complete";
          const current = i === activeIdx && phase !== "complete" && phase !== "error";
          return (
            <li
              key={s.label}
              className="flex items-center gap-3 border-b pb-3"
              style={{ borderColor: "var(--rule)" }}
            >
              <span
                className={
                  current ? "obs-pulse" : done ? "obs-dot done" : "obs-dot"
                }
              />
              <span
                className="text-sm"
                style={{
                  color: current || done ? "var(--ink)" : "var(--muted)",
                }}
              >
                {s.label}
              </span>
            </li>
          );
        })}
      </ol>

      {typeof sourceHint === "number" && sourceHint > 0 && (
        <p className="obs-mono mt-8 text-[0.7rem] text-[var(--muted)]">
          {sourceHint} sources found so far
        </p>
      )}
    </div>
  );
}
