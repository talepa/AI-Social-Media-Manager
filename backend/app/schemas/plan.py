"""
schemas/plan.py

Defines the Pydantic data models for the Planner Agent's output.

WHY: Using Pydantic models here ensures that the LLM's JSON output is
automatically validated and typed. If the LLM returns malformed data,
Pydantic will raise a clear validation error rather than passing bad data
downstream to the Writer Agent or API clients.
"""

from typing import List, Literal
from pydantic import BaseModel, Field


class PostIdea(BaseModel):
    # Represents a single content idea for one post on one platform.
    # This is the smallest unit of the weekly content plan.

    platform: Literal["LinkedIn", "Instagram", "Twitter", "Facebook"] = Field(
        ...,
        description="The social media platform this post is intended for.",
    )
    topic: str = Field(
        ...,
        description="The specific topic or theme for this post, derived from research.",
    )
    content_summary: str = Field(
        ...,
        description="A 2-3 sentence summary of what the post should say.",
    )
    suggested_publish_day: Literal[
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
    ] = Field(
        ...,
        description="The best day of the week to publish this post for maximum engagement.",
    )
    content_type: Literal["Educational", "Promotional", "Engagement", "Storytelling"] = Field(
        ...,
        description="The category/type of content to guide the Writer Agent's tone.",
    )


class WeeklyContentPlan(BaseModel):
    # Represents a full week of planned social media content.
    # 
    # WHY: Encapsulating all post ideas in one model keeps the data pipeline
    # clean — the Planner Agent returns ONE object, which the Writer Agent
    # then iterates over to generate each individual post.

    research_topic: str = Field(
        ...,
        description="The original topic that was researched to create this plan.",
    )
    strategy_summary: str = Field(
        ...,
        description="A high-level strategic summary explaining the content approach for the week.",
    )
    post_ideas: List[PostIdea] = Field(
        ...,
        description="A list of 5-7 post ideas scheduled across the week.",
    )
    target_audience: str = Field(
        ...,
        description="A description of the intended audience for this week's content.",
    )
