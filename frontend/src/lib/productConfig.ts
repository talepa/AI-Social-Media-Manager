import type { ResearchCategory } from "./productTypes";

export type ResearchModeId = "explore" | "compare" | "evaluate" | "academic" | "news";

export const RESEARCH_MODES: {
  id: ResearchModeId;
  label: string;
  blurb: string;
  category: ResearchCategory;
  planned?: boolean;
  plannedNote?: string;
}[] = [
  {
    id: "explore",
    label: "Explore",
    blurb: "General investigation — findings, sources, gaps, and conclusion.",
    category: "general",
  },
  {
    id: "compare",
    label: "Compare",
    blurb: "Two or more options side by side in the report.",
    category: "general",
    planned: true,
    plannedNote: "Shapes the report template — routing unchanged until phase 2.",
  },
  {
    id: "evaluate",
    label: "Evaluate",
    blurb: "Score a technology, product, or approach against evidence.",
    category: "founder",
    planned: true,
    plannedNote: "Shapes the report template — routing unchanged until phase 2.",
  },
  {
    id: "academic",
    label: "Academic",
    blurb: "Papers first, then web for context.",
    category: "academic",
  },
  {
    id: "news",
    label: "News",
    blurb: "Recent headlines and current web coverage.",
    category: "news_desk",
  },
];

export const DEPTH_PRESETS = [
  { id: 4, label: "Quick", sub: "4 per source" },
  { id: 6, label: "Standard", sub: "6 per source" },
  { id: 10, label: "Deep", sub: "10 per source" },
] as const;

export const PRINCIPLES = [
  "Research-first — not a chatbot",
  "Evidence over generic summaries",
  "Deterministic processing by default",
  "One optional Gemini call — not per source",
  "Transparent sources and citations",
] as const;

export const PIPELINE_STEPS = [
  { step: "01", title: "Ask", body: "Enter a research question and pick a mode." },
  { step: "02", title: "Route", body: "Source router picks web, news, papers, and/or GitHub." },
  { step: "03", title: "Gather", body: "LangGraph runs families in parallel — one failure does not stop the rest." },
  { step: "04", title: "Rank", body: "Results are deduped, scored, and ranked deterministically." },
  { step: "05", title: "Report", body: "Compile for free, or enhance with exactly one Gemini call." },
] as const;

export function estimateSourceCount(limit: number, sourceCount: number): number {
  return limit * sourceCount;
}

export function modeCategory(
  modeId: ResearchModeId,
  fallback: ResearchCategory,
): ResearchCategory {
  const mode = RESEARCH_MODES.find((m) => m.id === modeId);
  if (!mode) return fallback;
  if (modeId === "explore" || modeId === "compare") return fallback;
  return mode.category;
}
