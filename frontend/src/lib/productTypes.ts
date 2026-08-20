export type ResearchRunMode = "quick" | "research" | "deep" | "plan";

export type ResearchCategory =
  | "general"
  | "ai_engineer"
  | "founder"
  | "academic"
  | "news_desk";

export interface ResearchRoutingPlan {
  topic: string;
  search_query: string;
  papers_search_query?: string | null;
  domain: string;
  intent: string;
  run_mode: ResearchRunMode;
  sources: ("tavily" | "news" | "papers" | "github")[];
  limit: number;
  confidence: number;
  reason: string;
  method: "rules" | "llm" | "fallback";
  category: string;
}
