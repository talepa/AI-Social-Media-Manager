/** Investigation API types — mirror backend schemas/investigation.py */

export type InvestigationMode = "explore" | "compare" | "evaluate" | "academic";
export type InvestigationDepth = "quick" | "standard" | "deep";
export type SpecialistName = "web" | "academic" | "repository";
export type RunPhase =
  | "idle"
  | "accepted"
  | "director"
  | "specialists"
  | "evidence"
  | "synthesis"
  | "complete"
  | "error";

export interface DirectorRequest {
  question: string;
  mode: InvestigationMode;
  depth: InvestigationDepth;
  use_llm?: boolean;
}

export interface SubQuestion {
  id: string;
  text: string;
  specialist: SpecialistName;
  rationale?: string;
}

export interface InvestigationPlan {
  objective: string;
  mode: InvestigationMode;
  depth: InvestigationDepth;
  sub_questions: SubQuestion[];
  required_specialists: SpecialistName[];
  evidence_requirements?: string[];
  success_criteria?: string[];
  tool_budget: number;
  max_tasks: number;
  reason?: string;
}

export interface SourceRecord {
  id: string;
  type: "web" | "news" | "papers" | "github";
  title: string;
  url: string;
  content?: string;
  metadata?: Record<string, unknown>;
  specialist: SpecialistName;
  sub_question_id: string;
}

export interface ResearchFinding {
  id: string;
  sub_question_id: string;
  specialist: SpecialistName;
  claim: string;
  evidence_summary?: string;
  source_ids: string[];
  confidence: number;
}

export interface EvidenceClaim {
  id: string;
  claim: string;
  finding_ids: string[];
  supporting_source_ids: string[];
  contradicting_source_ids: string[];
  source_families: string[];
  confidence: number;
  strength: string;
  agreement_count: number;
  uncertainty_notes?: string | null;
}

export interface EvidenceAnalysis {
  claims: EvidenceClaim[];
  conflicts: { id: string; claim_a_id: string; claim_b_id: string; summary: string }[];
  gaps: { id: string; description: string }[];
  summary: string;
}

export interface InvestigationReport {
  headline: string;
  executive_summary: string;
  sections: { title: string; body: string; claim_ids: string[]; source_ids: string[] }[];
  cited_claim_ids: string[];
  cited_source_ids: string[];
  markdown: string;
  mode: "compile" | "llm";
}

export interface VerificationResult {
  passed: boolean;
  invalid_citations: string[];
  missing_sources: string[];
  notes: string[];
}

export interface InvestigationRunResponse {
  run_id: string;
  plan: InvestigationPlan;
  specialist_results: unknown[];
  sources: SourceRecord[];
  findings: ResearchFinding[];
  evidence: EvidenceAnalysis | null;
  report: InvestigationReport | null;
  verification: VerificationResult | null;
  tool_calls_used: number;
  llm_calls_used: number;
  use_llm: boolean;
  errors: Record<string, string>;
  events: ProgressEvent[];
}

export interface ProgressEvent {
  event_type: string;
  run_id?: string;
  [key: string]: unknown;
}

export interface NodeEvent {
  run_id: string;
  phase: string;
  tool_calls_used: number;
  llm_calls_used: number;
  use_llm: boolean;
  has_plan: boolean;
  finding_count: number;
  claim_count: number;
  has_report: boolean;
  error_count: number;
}

export type AgentStationId =
  | "director"
  | "web"
  | "academic"
  | "repository"
  | "evidence"
  | "synthesis";

export type StationStatus = "waiting" | "active" | "done" | "error";
