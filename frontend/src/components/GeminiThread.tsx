"use client";

import { useEffect, useRef, useState } from "react";
import { RUN_MODES } from "../lib/productConfig";
import type { ResearchRunMode } from "../lib/productTypes";
import { copyText, shareQuestion } from "../lib/shareResearch";
import type { DisplayTab } from "../lib/partitionResults";
import SourcePanel, {
  type MultiSourceResearchResult,
} from "./SourcePanel";
import type { ResearchRoutingPlan } from "../lib/productTypes";
import ResearchProgress from "./ResearchProgress";
import type { ChatMessage, ResearchProposal } from "./ResearchChat";
import AtelierMark from "./AtelierMark";

export type { ChatMessage, ResearchProposal };

function renderContent(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

function ShareIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M4 12v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-7M16 6l-4-4-4 4M12 2v14"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect x="9" y="9" width="11" height="11" rx="2" stroke="currentColor" strokeWidth="2" />
      <path d="M5 15V5a2 2 0 0 1 2-2h10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function UserMessage({
  content,
  onShare,
}: {
  content: string;
  onShare: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const [shared, setShared] = useState(false);

  return (
    <div className="gemini-msg gemini-msg--user">
      <div className="gemini-msg-user-row">
        <div className="gemini-msg-actions">
          <button
            type="button"
            className="gemini-action-btn"
            aria-label="Share question"
            onClick={async () => {
              try {
                const mode = await shareQuestion(content);
                setShared(mode === "shared");
                onShare();
                window.setTimeout(() => setShared(false), 2000);
              } catch {
                /* user cancelled share */
              }
            }}
          >
            {shared ? "✓" : <ShareIcon />}
          </button>
          <button
            type="button"
            className="gemini-action-btn"
            aria-label="Copy question"
            onClick={async () => {
              await copyText(content);
              setCopied(true);
              window.setTimeout(() => setCopied(false), 2000);
            }}
          >
            {copied ? "✓" : <CopyIcon />}
          </button>
        </div>
        <div className="gemini-bubble gemini-bubble--user">{content}</div>
      </div>
    </div>
  );
}

function AssistantMessage({
  msg,
  busy,
  expanding,
  onAllowOnce,
  onAllowAlways,
  onDismissProposal,
}: {
  msg: ChatMessage;
  busy?: boolean;
  expanding?: boolean;
  onAllowOnce: (id: string) => void;
  onAllowAlways: (id: string) => void;
  onDismissProposal: (id: string) => void;
}) {
  return (
    <div className="gemini-msg gemini-msg--assistant">
      <div className="gemini-assistant-row">
        <span className="gemini-assistant-mark" aria-hidden>
          <AtelierMark size={20} />
        </span>
        <div className="gemini-assistant-body">
          {msg.loading || expanding ? (
            <div className="gemini-thinking">
              <span className="gemini-thinking-shimmer" aria-hidden />
              <span className="chat-typing">
                <span />
                <span />
                <span />
              </span>
            </div>
          ) : (
            <div className="gemini-assistant-text">{renderContent(msg.content)}</div>
          )}

          {msg.proposal && msg.proposalStatus === "pending" && !msg.loading && (
            <div className="research-permission-card gemini-in">
              <p className="research-permission-kicker">Expand search</p>
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
    </div>
  );
}

export default function GeminiThread({
  isHome,
  topic,
  runMode,
  messages,
  input,
  busy,
  expanding,
  loadingResearch,
  result,
  routing,
  sourceTab,
  loadStage,
  onTopicChange,
  onRunModeChange,
  onInputChange,
  onSubmit,
  onSend,
  onAllowOnce,
  onAllowAlways,
  onDismissProposal,
  onSourceTabChange,
}: {
  isHome: boolean;
  topic: string;
  runMode: ResearchRunMode;
  messages: ChatMessage[];
  input: string;
  busy?: boolean;
  expanding?: boolean;
  loadingResearch?: boolean;
  result: MultiSourceResearchResult | null;
  routing?: ResearchRoutingPlan | null;
  sourceTab: DisplayTab | null;
  loadStage: number;
  onTopicChange: (v: string) => void;
  onRunModeChange: (m: ResearchRunMode) => void;
  onInputChange: (v: string) => void;
  onSubmit: () => void;
  onSend: () => void;
  onAllowOnce: (id: string) => void;
  onAllowAlways: (id: string) => void;
  onDismissProposal: (id: string) => void;
  onSourceTabChange: (tab: DisplayTab) => void;
}) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const hasThread = !isHome || messages.length > 0;
  const composerValue = hasThread ? input : topic;
  const composerDisabled = busy || loadingResearch || expanding;

  const firstAssistantIdx = messages.findIndex((m) => m.role === "assistant");
  const threadSplit =
    firstAssistantIdx >= 0 ? firstAssistantIdx + 1 : messages.length;
  const headMessages = messages.slice(0, threadSplit);
  const tailMessages = messages.slice(threadSplit);
  const showSources = Boolean(result && !loadingResearch);

  const scrollToBottom = (behavior: ScrollBehavior = "smooth") => {
    const viewport = viewportRef.current;
    if (!viewport) return;
    viewport.scrollTo({ top: viewport.scrollHeight, behavior });
  };

  useEffect(() => {
    scrollToBottom("smooth");
  }, [messages, loadingResearch, expanding, result, busy]);

  useEffect(() => {
    scrollToBottom("auto");
  }, [messages.length]);

  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [composerValue]);

  const handleComposerChange = (v: string) => {
    if (hasThread) onInputChange(v);
    else onTopicChange(v);
  };

  const handleSend = () => {
    if (hasThread) onSend();
    else onSubmit();
  };

  const renderMessage = (msg: ChatMessage) =>
    msg.role === "user" ? (
      <UserMessage key={msg.id} content={msg.content} onShare={() => undefined} />
    ) : (
      <AssistantMessage
        key={msg.id}
        msg={msg}
        busy={busy}
        expanding={expanding}
        onAllowOnce={onAllowOnce}
        onAllowAlways={onAllowAlways}
        onDismissProposal={onDismissProposal}
      />
    );

  return (
    <div className={`gemini-thread${hasThread ? " gemini-thread--active" : ""}`}>
      {!hasThread ? (
        <div className="gemini-empty gemini-in">
          <h1 className="gemini-greeting">What would you like to research?</h1>
          <p className="gemini-subgreeting">
            Ask anything — we route web, news, papers, and GitHub automatically.
          </p>
        </div>
      ) : (
        <div className="gemini-viewport" ref={viewportRef}>
          <div className="gemini-messages">
            {headMessages.map(renderMessage)}

            {loadingResearch && (
              <div className="gemini-msg gemini-msg--assistant">
                <div className="gemini-assistant-row">
                  <span className="gemini-assistant-mark" aria-hidden>
                    <AtelierMark size={20} />
                  </span>
                  <ResearchProgress
                    topic={topic.trim() || messages[0]?.content || "…"}
                    stageIndex={loadStage}
                    routingReason={routing?.reason}
                    routingSources={routing?.sources}
                  />
                </div>
              </div>
            )}

            {showSources && (
              <div className="gemini-sources gemini-in">
                <SourcePanel
                  result={result!}
                  routing={routing}
                  tab={sourceTab}
                  onTabChange={onSourceTabChange}
                />
              </div>
            )}

            {tailMessages.map(renderMessage)}

            <div ref={bottomRef} className="gemini-scroll-anchor" aria-hidden />
          </div>
        </div>
      )}

      <footer className="gemini-footer">
        {!hasThread && (
          <div className="gemini-compose-wrap">
            <div className="gemini-compose-glow" aria-hidden />
            <GeminiComposer
              inputRef={inputRef}
              value={composerValue}
              runMode={runMode}
              disabled={composerDisabled}
              placeholder="Ask Atelier"
              onRunModeChange={onRunModeChange}
              onChange={handleComposerChange}
              onSend={handleSend}
            />
          </div>
        )}

        {hasThread && (
          <GeminiComposer
            inputRef={inputRef}
            value={composerValue}
            runMode={runMode}
            disabled={composerDisabled}
            placeholder="Ask a follow-up…"
            onRunModeChange={onRunModeChange}
            onChange={handleComposerChange}
            onSend={handleSend}
          />
        )}

        <p className="gemini-disclaimer">
          Atelier gathers live sources — verify important claims before you act on them.
        </p>
      </footer>
    </div>
  );
}

function GeminiComposer({
  inputRef,
  value,
  runMode,
  disabled,
  placeholder,
  onRunModeChange,
  onChange,
  onSend,
}: {
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
  value: string;
  runMode: ResearchRunMode;
  disabled?: boolean;
  placeholder: string;
  onRunModeChange: (m: ResearchRunMode) => void;
  onChange: (v: string) => void;
  onSend: () => void;
}) {
  return (
    <div className="gemini-compose">
      <div className="gemini-mode-picker" role="tablist" aria-label="Research depth">
        {RUN_MODES.map((m) => (
          <button
            key={m.id}
            type="button"
            role="tab"
            aria-selected={runMode === m.id}
            className={`gemini-mode-btn${runMode === m.id ? " is-active" : ""}`}
            title={m.hint}
            disabled={disabled}
            onClick={() => onRunModeChange(m.id)}
          >
            {m.label}
          </button>
        ))}
      </div>
      <div className="gemini-compose-row">
        <textarea
          ref={inputRef}
          className="gemini-input"
          rows={1}
          value={value}
          placeholder={placeholder}
          aria-label={placeholder}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSend();
            }
          }}
        />
        <button
          type="button"
          className="gemini-send"
          disabled={disabled || !value.trim()}
          aria-label="Send"
          onClick={onSend}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden>
            <path
              fill="currentColor"
              d="M12 4l-1.4 1.4 6.6 6.6H4v2h13.2l-6.6 6.6L12 20l9.2-9.2L12 4z"
              transform="rotate(-90 12 12)"
            />
          </svg>
        </button>
      </div>
    </div>
  );
}
