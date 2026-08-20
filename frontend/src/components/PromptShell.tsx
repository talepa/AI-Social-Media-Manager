"use client";

import { useRef } from "react";
import { RUN_MODES } from "../lib/productConfig";
import type { ResearchRunMode } from "../lib/productTypes";

const EXAMPLES = [
  "How beetroot helps daily health and routine",
  "LangGraph vs CrewAI for production agents",
  "Latest EU AI Act enforcement news",
  "What do clinical studies say about beetroot and blood pressure?",
];

export default function PromptShell({
  topic,
  runMode,
  busy,
  onTopicChange,
  onRunModeChange,
  onSubmit,
}: {
  topic: string;
  runMode: ResearchRunMode;
  busy?: boolean;
  onTopicChange: (v: string) => void;
  onRunModeChange: (m: ResearchRunMode) => void;
  onSubmit: () => void;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);

  return (
    <section className="home-shell fade-in">
      <div className="home-hero">
        <p className="home-kicker">Atelier Research</p>
        <h1 className="home-title">Research anything through one chat.</h1>
        <p className="home-lead">
          Ask like you would on ChatGPT — we route web, news, papers, and GitHub,
          then keep the conversation going with cited follow-ups.
        </p>
      </div>

      <div className="home-compose">
        <div className="home-compose-card">
          <div className="prompt-mode-row" role="tablist" aria-label="Research depth">
            {RUN_MODES.map((m) => (
              <button
                key={m.id}
                type="button"
                role="tab"
                aria-selected={runMode === m.id}
                className={`prompt-mode-btn${runMode === m.id ? " is-active" : ""}`}
                title={m.hint}
                onClick={() => onRunModeChange(m.id)}
              >
                {m.icon} {m.label}
              </button>
            ))}
          </div>

          <div className="home-input-row">
            <textarea
              ref={ref}
              className="home-input"
              value={topic}
              rows={1}
              placeholder="Say more…"
              aria-label="Research question"
              onChange={(e) => onTopicChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  onSubmit();
                }
              }}
            />
            <button
              type="button"
              className="home-send"
              disabled={busy || !topic.trim()}
              onClick={onSubmit}
              aria-label="Start research"
            >
              ↑
            </button>
          </div>
        </div>
        <p className="home-hint">
          {RUN_MODES.find((m) => m.id === runMode)?.hint ?? "Enter to research"}
        </p>
      </div>

      <div className="home-examples">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            type="button"
            className="prompt-example"
            onClick={() => {
              onTopicChange(ex);
              ref.current?.focus();
            }}
          >
            {ex}
          </button>
        ))}
      </div>
    </section>
  );
}
