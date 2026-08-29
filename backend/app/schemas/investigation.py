"""
schemas/investigation.py

Structured models for the Director -> Specialists -> Evidence -> Synthesis
pipeline (see ~/Downloads/ATELIER_FINAL_ARCHITECTURE.md). Kept separate from
schemas/research.py and schemas/session.py: this is a new orchestration model
built alongside the existing ones, not a replacement.

Naming note: the target spec calls the Director's output "ResearchPlan" —
renamed to InvestigationPlan here because schemas/research.py already defines
a different ResearchPlan (the "plan mode" action-plan-with-steps produced by
plan_synthesizer.py). The two are unrelated concepts that happen to share a
name in the source spec.
"""

from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

InvestigationMode = Literal["explore", "compare", "evaluate", "academic"]
InvestigationDepth = Literal["quick", "standard", "deep"]
SpecialistName = Literal["web", "academic", "repository"]

# Depth -> (max_tasks, tool_call_budget), per architecture spec section 11.
DEPTH_BUDGETS: dict[InvestigationDepth, tuple[int, int]] = {
    "quick": (3, 6),
    "standard": (5, 12),
    "deep": (8, 20),
}


class SubQuestion(BaseModel):
    id: str = Field(..., description="Stable short id, e.g. 'Q1'")
    text: str = Field(..., description="The specific sub-question to investigate")
    specialist: SpecialistName = Field(
        ..., description="Which specialist should answer this sub-question"
    )
    rationale: str = Field(
        default="", description="Why this sub-question matters for the overall objective"
    )


class InvestigationPlan(BaseModel):
    """Director's structured research plan for one investigation run."""

    objective: str = Field(..., description="One-sentence restatement of what's being decided")
    mode: InvestigationMode
    depth: InvestigationDepth
    sub_questions: List[SubQuestion] = Field(default_factory=list)
    required_specialists: List[SpecialistName] = Field(
        default_factory=list,
        description="Distinct specialists actually needed for this question",
    )
    evidence_requirements: List[str] = Field(
        default_factory=list,
        description="What kinds of evidence would make the answer trustworthy",
    )
    freshness_requirement: Optional[str] = Field(
        default=None,
        description="e.g. 'last 12 months' if recency matters, else null",
    )
    success_criteria: List[str] = Field(default_factory=list)
    max_iterations: int = Field(default=1, ge=1, le=3)
    tool_budget: int = Field(..., description="Total tool calls allowed across all specialists")
    max_tasks: int = Field(..., description="Total sub-questions allowed across all specialists")
    reason: str = Field(default="", description="Director's short rationale for this plan")


class SourceRecord(BaseModel):
    """A single retrieved source with a stable ID for citation tracking."""

    id: str = Field(..., description="Stable ID, e.g. 'WEB-001', 'PAPER-003'")
    type: Literal["web", "news", "papers", "github"] = Field(
        ..., description="Source family"
    )
    title: str
    url: str
    content: str = Field(default="", description="Snippet or abstract, max 600 chars")
    metadata: dict = Field(
        default_factory=dict,
        description="Source-specific metadata (authors, stars, citations, etc.)",
    )
    specialist: SpecialistName = Field(
        ..., description="Which specialist retrieved this source"
    )
    sub_question_id: str = Field(
        ..., description="The SubQuestion.id this source answers"
    )
    retrieved_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ResearchFinding(BaseModel):
    """A structured finding produced by a specialist agent."""

    id: str = Field(..., description="Stable ID, e.g. 'F-001'")
    sub_question_id: str
    specialist: SpecialistName
    claim: str = Field(..., description="One-sentence factual claim")
    evidence_summary: str = Field(
        default="", description="Supporting evidence summary"
    )
    source_ids: List[str] = Field(
        default_factory=list,
        description="SourceRecord IDs that support this finding",
    )
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Specialist's confidence in this finding",
    )
    methodology_note: Optional[str] = Field(
        default=None,
        description="Note on evidence quality or methodology",
    )


class SpecialistResult(BaseModel):
    """Output of one specialist agent run on one sub-question."""

    specialist: SpecialistName
    sub_question_id: str
    sources: List[SourceRecord] = Field(default_factory=list)
    findings: List[ResearchFinding] = Field(default_factory=list)
    tool_calls_used: int = 0
    llm_calls_used: int = 0
    error: Optional[str] = None


EvidenceStrength = Literal["strong", "moderate", "weak", "insufficient"]


class EvidenceClaim(BaseModel):
    """A consolidated claim produced by the Evidence Analyst."""

    id: str = Field(..., description="Stable ID, e.g. 'CLAIM-001'")
    claim: str
    finding_ids: List[str] = Field(default_factory=list)
    supporting_source_ids: List[str] = Field(default_factory=list)
    contradicting_source_ids: List[str] = Field(default_factory=list)
    source_families: List[str] = Field(
        default_factory=list,
        description="Distinct source families backing this claim (web/news/papers/github)",
    )
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    strength: EvidenceStrength = "moderate"
    agreement_count: int = Field(
        default=0,
        description="How many independent findings/families support the claim",
    )
    uncertainty_notes: Optional[str] = None
    sub_question_ids: List[str] = Field(default_factory=list)


class EvidenceConflict(BaseModel):
    """Two claims that appear to disagree."""

    id: str = Field(..., description="Stable ID, e.g. 'CONFLICT-001'")
    claim_a_id: str
    claim_b_id: str
    summary: str
    source_ids: List[str] = Field(default_factory=list)


class EvidenceGap(BaseModel):
    """Missing evidence relative to the plan or sub-questions."""

    id: str = Field(..., description="Stable ID, e.g. 'GAP-001'")
    description: str
    related_sub_question_ids: List[str] = Field(default_factory=list)
    suggested_specialist: Optional[SpecialistName] = None


class EvidenceAnalysis(BaseModel):
    """Full Evidence Analyst output for one investigation run."""

    claims: List[EvidenceClaim] = Field(default_factory=list)
    conflicts: List[EvidenceConflict] = Field(default_factory=list)
    gaps: List[EvidenceGap] = Field(default_factory=list)
    summary: str = ""
    llm_calls_used: int = 0


class ReportSection(BaseModel):
    title: str
    body: str
    claim_ids: List[str] = Field(default_factory=list)
    source_ids: List[str] = Field(default_factory=list)


class InvestigationReport(BaseModel):
    """Cited research report grounded in verified evidence claims."""

    headline: str
    executive_summary: str
    sections: List[ReportSection] = Field(default_factory=list)
    cited_claim_ids: List[str] = Field(default_factory=list)
    cited_source_ids: List[str] = Field(default_factory=list)
    markdown: str = ""
    mode: Literal["compile", "llm"] = "compile"


class VerificationResult(BaseModel):
    """Citation validation for the synthesized report."""

    passed: bool = True
    invalid_citations: List[str] = Field(default_factory=list)
    missing_sources: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class DirectorRequest(BaseModel):
    question: str = Field(..., min_length=1)
    mode: InvestigationMode = "explore"
    depth: InvestigationDepth = "standard"


class DirectorResponse(BaseModel):
    """Phase-1 response shape (plan only). Kept for compatibility."""

    run_id: str
    plan: InvestigationPlan


class InvestigationRunResponse(BaseModel):
    """Full investigation run after Director + Specialists + Evidence + Synthesis."""

    run_id: str
    plan: InvestigationPlan
    specialist_results: List[SpecialistResult] = Field(default_factory=list)
    sources: List[SourceRecord] = Field(default_factory=list)
    findings: List[ResearchFinding] = Field(default_factory=list)
    evidence: Optional[EvidenceAnalysis] = None
    report: Optional[InvestigationReport] = None
    verification: Optional[VerificationResult] = None
    tool_calls_used: int = 0
    llm_calls_used: int = 0
    events: List[dict] = Field(default_factory=list)


class InvestigationRunStatusResponse(BaseModel):
    """Stored run lookup (in-memory; lost on process restart)."""

    run_id: str
    status: Literal["running", "completed", "failed"]
    question: str = ""
    mode: str = "explore"
    depth: str = "standard"
    created_at: float
    updated_at: float
    events: List[dict] = Field(default_factory=list)
    result: Optional[InvestigationRunResponse] = None
    error: Optional[str] = None
