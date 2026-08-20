import type { ChatMessage } from "../components/GeminiThread";
import type { DisplayTab } from "./partitionResults";
import type { ResearchRunMode } from "./productTypes";

const STORAGE_KEY = "atelier_chat_sessions_v1";
const MAX_SESSIONS = 40;

export interface StoredChatSession {
  id: string;
  title: string;
  topic: string;
  runMode: ResearchRunMode;
  messages: ChatMessage[];
  result: unknown | null;
  sourceTab: DisplayTab | null;
  createdAt: number;
  updatedAt: number;
}

function readAll(): StoredChatSession[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as StoredChatSession[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeAll(sessions: StoredChatSession[]) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions.slice(0, MAX_SESSIONS)));
}

export function loadChatSessions(): StoredChatSession[] {
  return readAll().sort((a, b) => b.updatedAt - a.updatedAt);
}

export function upsertChatSession(session: StoredChatSession) {
  const all = readAll().filter((s) => s.id !== session.id);
  all.unshift(session);
  writeAll(all);
}

export function deleteChatSession(id: string) {
  writeAll(readAll().filter((s) => s.id !== id));
}

export function getChatSession(id: string): StoredChatSession | null {
  return readAll().find((s) => s.id === id) ?? null;
}

export function sessionTitle(messages: ChatMessage[], topic: string): string {
  const first = messages.find((m) => m.role === "user")?.content?.trim();
  const t = first || topic.trim() || "New research";
  return t.length > 56 ? `${t.slice(0, 53)}…` : t;
}

export function formatSessionTime(ts: number): string {
  const diff = Date.now() - ts;
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(ts).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
