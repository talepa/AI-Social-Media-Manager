"use client";

import { useState } from "react";
import type { InvestigationDepth, InvestigationMode } from "@/lib/investigationTypes";

const MODES: { id: InvestigationMode; label: string; hint: string }[] = [
  { id: "explore", label: "Explore", hint: "General investigation" },
  { id: "compare", label: "Compare", hint: "Trade-offs between options" },
  { id: "evaluate", label: "Evaluate", hint: "Production readiness" },
  { id: "academic", label: "Academic", hint: "Paper-first research" },
];

const DEPTHS: { id: InvestigationDepth; label: string; hint: string }[] = [
  { id: "quick", label: "Quick", hint: "3 tasks · 6 tools" },
  { id: "standard", label: "Standard", hint: "5 tasks · 12 tools" },
  { id: "deep", label: "Deep", hint: "8 tasks · 20 tools" },
];

export function ResearchComposer({
  onSubmit,
  busy,
}: {
  onSubmit: (payload: {
    question: string;
    mode: InvestigationMode;
    depth: InvestigationDepth;
    use_llm: boolean;
  }) => void;
  busy?: boolean;
}) {
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState<InvestigationMode>("explore");
  const [depth, setDepth] = useState<InvestigationDepth>("standard");
  const [useLlm, setUseLlm] = useState(false);

  return (
    <form
      className="obs-panel overflow-hidden"
      onSubmit={(e) => {
        e.preventDefault();
        const q = question.trim();
        if (!q || busy) return;
        onSubmit({ question: q, mode, depth, use_llm: useLlm });
      }}
    >
      <div
        className="border-b px-5 py-3 md:px-6"
        style={{ borderColor: "var(--rule)" }}
      >
        <p className="obs-kicker">Atelier / Commission</p>
      </div>

      <div className="grid md:grid-cols-[1.4fr_1fr]">
        <div className="border-b p-5 md:border-b-0 md:border-r md:p-6" style={{ borderColor: "var(--rule)" }}>
          <label className="obs-kicker" htmlFor="brief">
            Investigation brief
          </label>
          <textarea
            id="brief"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows={10}
            placeholder="Should we adopt X for production? What are the risks, alternatives, and evidence?"
            className="mt-4 w-full resize-y border-0 bg-transparent text-lg outline-none md:text-xl"
            style={{
              fontFamily: "var(--serif)",
              lineHeight: 1.45,
              minHeight: "14rem",
            }}
            required
          />
        </div>

        <aside className="p-5 md:p-6">
          <p className="obs-kicker mb-4">Research parameters</p>

          <p className="obs-mono mb-2 text-[0.65rem] tracking-[0.14em] text-[var(--muted)]">
            Mode
          </p>
          <div className="mb-6 flex flex-col gap-2">
            {MODES.map((m) => (
              <label key={m.id} className="flex cursor-pointer items-start gap-3">
                <input
                  type="radio"
                  name="mode"
                  checked={mode === m.id}
                  onChange={() => setMode(m.id)}
                  className="mt-1 accent-[var(--signal)]"
                />
                <span>
                  <span className="block text-sm">{m.label}</span>
                  <span className="obs-mono text-[0.65rem] text-[var(--muted)]">
                    {m.hint}
                  </span>
                </span>
              </label>
            ))}
          </div>

          <p className="obs-mono mb-2 text-[0.65rem] tracking-[0.14em] text-[var(--muted)]">
            Depth
          </p>
          <div className="mb-6 flex flex-col gap-2">
            {DEPTHS.map((d) => (
              <label key={d.id} className="flex cursor-pointer items-start gap-3">
                <input
                  type="radio"
                  name="depth"
                  checked={depth === d.id}
                  onChange={() => setDepth(d.id)}
                  className="mt-1 accent-[var(--signal)]"
                />
                <span>
                  <span className="block text-sm">{d.label}</span>
                  <span className="obs-mono text-[0.65rem] text-[var(--muted)]">
                    {d.hint}
                  </span>
                </span>
              </label>
            ))}
          </div>

          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              checked={useLlm}
              onChange={(e) => setUseLlm(e.target.checked)}
              className="mt-1 accent-[var(--signal)]"
            />
            <span>
              <span className="block text-sm">LLM polish</span>
              <span className="obs-mono text-[0.65rem] text-[var(--muted)]">
                Optional Gemini for evidence / narrative
              </span>
            </span>
          </label>
        </aside>
      </div>

      <div
        className="flex flex-wrap items-center justify-between gap-3 border-t px-5 py-4 md:px-6"
        style={{ borderColor: "var(--rule)" }}
      >
        <p className="obs-mono text-[0.65rem] text-[var(--muted)]">
          Pipeline · Director → MCP specialists → Evidence → Report
        </p>
        <button type="submit" className="obs-btn" disabled={busy || !question.trim()}>
          {busy ? "Commissioning…" : "Commission investigation"}
        </button>
      </div>
    </form>
  );
}
