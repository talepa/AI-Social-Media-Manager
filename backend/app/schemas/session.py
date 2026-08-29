"""
schemas/session.py

Request/response models for the checkpointed session API (app/api/session.py).

Kept separate from schemas/research.py: that file is the stable vocabulary for
the existing stateless endpoints, while thread/interrupt/decision concepts are
specific to the new session flow and have no reuse value there.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.research import MultiSourceResearchResult, ResearchRoutingPlan, SourceType


class SessionStartRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    run_mode: str = Field(default="research", description="quick | research | deep | plan")


class SessionStartResponse(BaseModel):
    thread_id: str
    research: MultiSourceResearchResult
    opening_message: str
    run_mode: str
    routing: Optional[ResearchRoutingPlan] = None


class SessionMessageRequest(BaseModel):
    question: str = Field(..., min_length=1)
    auto_expand: bool = Field(
        default=False,
        description="Auto-accept an expand-research proposal instead of pausing for approval",
    )
    auto_mode_switch: bool = Field(
        default=False,
        description="Auto-accept a mode-switch proposal instead of pausing for approval",
    )


class InterruptPayload(BaseModel):
    type: Literal["expand_research", "mode_switch"]
    reason: str
    user_message: str = ""
    # expand_research fields
    query: Optional[str] = None
    sources: Optional[List[SourceType]] = None
    # mode_switch fields
    suggested_mode: Optional[str] = None
    current_mode: Optional[str] = None


class SessionTurnResponse(BaseModel):
    thread_id: str
    status: Literal["answered", "paused"]
    answer: Optional[str] = None
    interrupt: Optional[InterruptPayload] = None
    research: Optional[MultiSourceResearchResult] = None
    plan: Optional[dict] = None
    plan_markdown: Optional[str] = None
    run_mode: str


class SessionDecisionRequest(BaseModel):
    decision: Literal["accept", "decline"]
