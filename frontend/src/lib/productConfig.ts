import type { ResearchRunMode } from "./productTypes";

export type { ResearchRunMode };

export const RUN_MODES: {
  id: ResearchRunMode;
  label: string;
  hint: string;
  icon: string;
}[] = [
  {
    id: "quick",
    label: "Quick",
    hint: "Fast web scan · ~4 sources",
    icon: "⚡",
  },
  {
    id: "research",
    label: "Research",
    hint: "Balanced evidence gather",
    icon: "⌕",
  },
  {
    id: "deep",
    label: "Deep",
    hint: "Maximum sources · thorough",
    icon: "◈",
  },
  {
    id: "plan",
    label: "Plan",
    hint: "Structured template plan from your sources",
    icon: "◎",
  },
];

export const DEPTH_PRESETS = [
  { id: 4, label: "Quick", sub: "4 per source" },
  { id: 6, label: "Standard", sub: "6 per source" },
  { id: 10, label: "Deep", sub: "10 per source" },
] as const;

export const PRINCIPLES = [
  "Ask anything — we route sources for you",
  "Evidence over generic summaries",
  "Deterministic gather by default",
  "One optional Gemini call for reports",
  "Transparent routing and citations",
] as const;

export const PIPELINE_STEPS = [
  { step: "01", title: "Ask", body: "Type your question — no category chips." },
  { step: "02", title: "Route", body: "Rules infer domain, intent, and sources." },
  { step: "03", title: "Gather", body: "Web, news, papers, GitHub in parallel." },
  { step: "04", title: "Rank", body: "Dedupe, score, and rank deterministically." },
  { step: "05", title: "Report", body: "Compile free, or enhance with one AI call." },
] as const;

export function estimateSourceCount(limit: number, sourceCount: number): number {
  return limit * sourceCount;
}

export function formatDomain(domain: string): string {
  return domain.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatSources(sources: string[]): string {
  const labels: Record<string, string> = {
    tavily: "Web",
    news: "News",
    papers: "Papers",
    github: "GitHub",
  };
  return sources.map((s) => labels[s] ?? s).join(" · ");
}
