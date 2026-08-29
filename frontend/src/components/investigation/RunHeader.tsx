"use client";

export function RunHeader({
  runId,
  question,
  mode,
  depth,
  tools,
  llms,
}: {
  runId: string | null;
  question: string;
  mode?: string;
  depth?: string;
  tools?: number;
  llms?: number;
}) {
  return (
    <div
      className="flex flex-wrap items-end justify-between gap-4 border-b px-4 py-3 md:px-5"
      style={{ borderColor: "var(--rule)" }}
    >
      <div>
        <p className="obs-kicker">
          Run {runId ? runId.slice(0, 8).toUpperCase() : "—"}
        </p>
        <h1 className="obs-display mt-1 max-w-3xl text-xl md:text-2xl">
          {question || "Awaiting brief…"}
        </h1>
      </div>
      <div className="obs-mono flex flex-wrap gap-4 text-[0.65rem] tracking-[0.08em] text-[var(--muted)]">
        {mode && <span>MODE {mode}</span>}
        {depth && <span>DEPTH {depth}</span>}
        {typeof tools === "number" && <span>TOOLS {tools}</span>}
        {typeof llms === "number" && <span>LLM {llms}</span>}
      </div>
    </div>
  );
}
