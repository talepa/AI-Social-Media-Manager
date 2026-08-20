"use client";

import AtelierMark from "./AtelierMark";
import {
  formatSessionTime,
  type StoredChatSession,
} from "../lib/chatHistory";

export default function ChatSidebar({
  sessions,
  activeId,
  open,
  onNewChat,
  onSelect,
  onDelete,
  onToggle,
}: {
  sessions: StoredChatSession[];
  activeId: string | null;
  open: boolean;
  onNewChat: () => void;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onToggle: () => void;
}) {
  return (
    <>
      <button
        type="button"
        className="sidebar-toggle"
        aria-label={open ? "Close sidebar" : "Open chat history"}
        onClick={onToggle}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden>
          <path
            fill="currentColor"
            d="M4 5h16a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Zm2 2v10h12V7H6Zm2 2h8v1.5H8V9Zm0 3h6v1.5H8V12Z"
          />
        </svg>
      </button>

      <aside
        className={`chat-sidebar${open ? " is-open" : ""}`}
        aria-label="Chat history"
      >
        <div className="chat-sidebar-head">
          <div className="chat-sidebar-brand">
            <AtelierMark size={20} />
            <span>History</span>
          </div>
          <button type="button" className="chat-sidebar-new" onClick={onNewChat}>
            <span aria-hidden>+</span>
            New chat
          </button>
        </div>

        <div className="chat-sidebar-list">
          {sessions.length === 0 ? (
            <p className="chat-sidebar-empty">No chats yet — ask anything to start.</p>
          ) : (
            sessions.map((s) => (
              <div
                key={s.id}
                className={`chat-sidebar-item${activeId === s.id ? " is-active" : ""}`}
              >
                <button
                  type="button"
                  className="chat-sidebar-item-btn"
                  onClick={() => onSelect(s.id)}
                >
                  <span className="chat-sidebar-item-title">{s.title}</span>
                  <span className="chat-sidebar-item-time">
                    {formatSessionTime(s.updatedAt)}
                  </span>
                </button>
                <button
                  type="button"
                  className="chat-sidebar-item-delete"
                  aria-label={`Delete ${s.title}`}
                  onClick={() => onDelete(s.id)}
                >
                  ×
                </button>
              </div>
            ))
          )}
        </div>
      </aside>

      {open ? (
        <button
          type="button"
          className="chat-sidebar-backdrop"
          aria-label="Close sidebar"
          onClick={onToggle}
        />
      ) : null}
    </>
  );
}
