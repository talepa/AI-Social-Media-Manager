"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { InvestigationDepth, InvestigationMode } from "@/lib/investigationTypes";

const EXAMPLES = [
  "What is the difference between loop engineering and prompt engineering?",
  "Is LangGraph ready for production agents?",
  "Compare RAG vs fine-tuning for internal docs Q&A",
];

export function SearchBox({
  initial = "",
  autofocus = false,
}: {
  initial?: string;
  autofocus?: boolean;
}) {
  const router = useRouter();
  const [question, setQuestion] = useState(initial);
  const [mode, setMode] = useState<InvestigationMode>("explore");
  const [depth, setDepth] = useState<InvestigationDepth>("standard");
  const [showOptions, setShowOptions] = useState(false);

  function submit(q?: string) {
    const text = (q ?? question).trim();
    if (!text) return;
    sessionStorage.setItem(
      "atelier:commission",
      JSON.stringify({ question: text, mode, depth, use_llm: false }),
    );
    router.push("/investigate");
  }

  return (
    <div className="w-full max-w-2xl">
      <form
        className="obs-panel overflow-hidden shadow-sm"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <label className="sr-only" htmlFor="q">
          Your question
        </label>
        <textarea
          id="q"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          autoFocus={autofocus}
          rows={3}
          placeholder="Ask a technical question…"
          className="w-full resize-none border-0 bg-transparent px-5 py-4 text-lg outline-none"
          style={{ fontFamily: "var(--serif)", lineHeight: 1.45 }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
        />
        <div
          className="flex flex-wrap items-center justify-between gap-3 border-t px-4 py-3"
          style={{ borderColor: "var(--rule)" }}
        >
          <button
            type="button"
            className="obs-mono text-[0.7rem] text-[var(--muted)] hover:text-[var(--ink)]"
            onClick={() => setShowOptions((v) => !v)}
          >
            {showOptions ? "Hide options" : "Options"}
          </button>
          <button type="submit" className="obs-btn" disabled={!question.trim()}>
            Search
          </button>
        </div>
        {showOptions && (
          <div
            className="grid gap-4 border-t px-4 py-4 sm:grid-cols-2"
            style={{ borderColor: "var(--rule)", background: "var(--surface)" }}
          >
            <label className="block text-sm">
              <span className="obs-mono text-[0.65rem] text-[var(--muted)]">Type</span>
              <select
                className="mt-1 w-full border px-2 py-2"
                style={{ borderColor: "var(--rule)", background: "var(--bg)" }}
                value={mode}
                onChange={(e) => setMode(e.target.value as InvestigationMode)}
              >
                <option value="explore">Explore</option>
                <option value="compare">Compare</option>
                <option value="evaluate">Evaluate</option>
                <option value="academic">Academic</option>
              </select>
            </label>
            <label className="block text-sm">
              <span className="obs-mono text-[0.65rem] text-[var(--muted)]">Depth</span>
              <select
                className="mt-1 w-full border px-2 py-2"
                style={{ borderColor: "var(--rule)", background: "var(--bg)" }}
                value={depth}
                onChange={(e) => setDepth(e.target.value as InvestigationDepth)}
              >
                <option value="quick">Quick</option>
                <option value="standard">Standard</option>
                <option value="deep">Deep</option>
              </select>
            </label>
          </div>
        )}
      </form>

      <div className="mt-5 flex flex-wrap gap-2">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            type="button"
            className="rounded-full border px-3 py-1.5 text-left text-xs text-[var(--graphite)] hover:border-[var(--signal)] hover:text-[var(--ink)]"
            style={{ borderColor: "var(--rule)", background: "var(--surface)" }}
            onClick={() => {
              setQuestion(ex);
              submit(ex);
            }}
          >
            {ex.length > 56 ? ex.slice(0, 53) + "…" : ex}
          </button>
        ))}
      </div>
    </div>
  );
}
