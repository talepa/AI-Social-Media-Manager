"use client";

import { useEffect, useRef } from "react";

export type ResearchProposal = {
  query: string;
  sources: string[];
  reason: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  loading?: boolean;
  proposal?: ResearchProposal;
  proposalStatus?: "pending" | "accepted" | "dismissed";
};

const SUGGESTIONS = [
  "Find GitHub repos for this",
  "Best way to learn this",
  "Compare them in more detail",
  "What are the trade-offs?",
];

function renderContent(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

export default function ResearchChat({
  messages,
  input,
  busy,
  loadingResearch,
  expanding,
  onInputChange,
  onSend,
  onSuggestion,
  onAllowOnce,
  onAllowAlways,
  onDismissProposal,
}: {
  messages: ChatMessage[];
  input: string;
  busy?: boolean;
  loadingResearch?: boolean;
  expanding?: boolean;
  onInputChange: (v: string) => void;
  onSend: () => void;
  onSuggestion: (text: string) => void;
  onAllowOnce: (messageId: string) => void;
  onAllowAlways: (messageId: string) => void;
  onDismissProposal: (messageId: string) => void;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loadingResearch, expanding]);

  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  }, [input]);

  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant" && !m.loading);

  return (
    <div className="chat-pane">
      <div className="chat-pane-head">
        <div className="chat-pane-badge">Live session</div>
        <h2 className="chat-pane-title">Say more</h2>
        <p className="chat-pane-lead">
          Follow-ups stay on-topic. When new sources are needed, you choose allow once or always.
        </p>
      </div>

      <div className="chat-thread" role="log" aria-live="polite">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`chat-row chat-row--${msg.role}${msg.loading ? " is-loading" : ""}`}
          >
            <div className={`chat-avatar chat-avatar--${msg.role}`} aria-hidden>
              {msg.role === "user" ? "You" : "A"}
            </div>
            <div className="chat-stack">
              <div className={`chat-bubble chat-bubble--${msg.role}`}>
                {msg.loading || expanding ? (
                  <span className="chat-typing">
                    <span />
                    <span />
                    <span />
                  </span>
                ) : (
                  <div className="chat-bubble-text">{renderContent(msg.content)}</div>
                )}
              </div>

              {msg.proposal && msg.proposalStatus === "pending" && !msg.loading && (
                <div className="research-permission-card">
                  <p className="research-permission-kicker">Switch search</p>
                  <p className="research-permission-query">“{msg.proposal.query}”</p>
                  <p className="research-permission-reason">{msg.proposal.reason}</p>
                  <p className="research-permission-sources">
                    Sources: {msg.proposal.sources.join(" · ")}
                  </p>
                  <div className="research-permission-actions">
                    <button
                      type="button"
                      className="perm-btn perm-btn--primary"
                      disabled={busy || expanding}
                      onClick={() => onAllowOnce(msg.id)}
                    >
                      Allow once
                    </button>
                    <button
                      type="button"
                      className="perm-btn perm-btn--ghost"
                      disabled={busy || expanding}
                      onClick={() => onAllowAlways(msg.id)}
                    >
                      Always allow
                    </button>
                    <button
                      type="button"
                      className="perm-btn perm-btn--muted"
                      disabled={busy || expanding}
                      onClick={() => onDismissProposal(msg.id)}
                    >
                      Not now
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {loadingResearch && (
          <div className="chat-row chat-row--assistant is-loading">
            <div className="chat-avatar chat-avatar--assistant">A</div>
            <div className="chat-bubble chat-bubble--assistant">
              <span className="chat-typing">
                <span />
                <span />
                <span />
              </span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {lastAssistant && !loadingResearch && !busy && (
        <div className="chat-suggestions">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              type="button"
              className="chat-suggestion"
              onClick={() => onSuggestion(s)}
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <div className="chat-compose">
        <div className="chat-compose-inner">
          <textarea
            ref={inputRef}
            className="chat-input"
            rows={1}
            value={input}
            placeholder="Ask a follow-up…"
            aria-label="Follow-up message"
            disabled={busy || loadingResearch || expanding}
            onChange={(e) => onInputChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                onSend();
              }
            }}
          />
          <button
            type="button"
            className="chat-send"
            disabled={busy || loadingResearch || expanding || !input.trim()}
            onClick={onSend}
            aria-label="Send message"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden>
              <path
                fill="currentColor"
                d="M3.4 20.6 21 12 3.4 3.4l1.8 7.2L16 12l-10.8 1.4-1.8 7.2z"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
