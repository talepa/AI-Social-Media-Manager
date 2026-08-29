export interface PlanStep {
  title: string;
  detail: string;
  timeframe?: string | null;
}

export interface PlanResource {
  title: string;
  url: string;
  kind: string;
  note?: string | null;
}

export interface PlanSection {
  id: string;
  title: string;
  items: string[];
  steps: PlanStep[];
  resources: PlanResource[];
}

export interface ResearchPlan {
  topic: string;
  template: string;
  headline: string;
  goal: string;
  success_criteria: string[];
  sections: PlanSection[];
  next_actions: string[];
  mode: "compile" | "llm";
}

export const PLAN_TEMPLATE_LABELS: Record<string, string> = {
  compare: "Comparison",
  learning: "Learning path",
  build: "Build & ship",
  health: "Health routine",
  business: "Go-to-market",
  evaluate: "Evaluation",
  general: "Action plan",
};
