"""
schemas/content.py

Defines the Pydantic output models for the Writer Agent (Module 6).

WHY separate from plan.py?
- plan.py defines the INPUT to the writer (what to write about).
- content.py defines the OUTPUT of the writer (the actual written content).
- Keeping schemas separate by responsibility makes each one smaller,
  easier to test, and easier for future agents (Reviewer, Publisher) to import
  only what they need.
"""

from typing import List, Literal
from pydantic import BaseModel, Field


class WrittenPost(BaseModel):
    # Represents a single fully-written, ready-to-publish social media post.
    # 
    # This is the atomic unit that flows out of the Writer Agent and into
    # the Reviewer Agent (Module 7).

    platform: Literal["LinkedIn", "Instagram", "Twitter", "Facebook"] = Field(
        ...,
        description="The social media platform this post is written for.",
    )
    topic: str = Field(
        ...,
        description="The topic of this post, carried forward from the PostIdea.",
    )
    body: str = Field(
        ...,
        description=(
            "The main post body text. "
            "LinkedIn: 150-300 words. Instagram: 100-150 words. Twitter: under 280 chars."
        ),
    )
    hashtags: List[str] = Field(
        ...,
        description=(
            "A list of relevant hashtags WITHOUT the # symbol. "
            "LinkedIn: 3-5. Instagram: 10-15. Twitter: 1-2."
        ),
    )
    call_to_action: str = Field(
        ...,
        description=(
            "A single clear CTA at the end of the post "
            "(e.g., 'Share your thoughts below', 'Click the link in bio', 'Retweet if you agree')."
        ),
    )
    content_type: Literal["Educational", "Promotional", "Engagement", "Storytelling"] = Field(
        ...,
        description="The content type carried forward from the plan — helps the Reviewer audit tone.",
    )
    brand_voice_applied: str = Field(
        ...,
        description=(
            "A short note explaining which brand voice rules were applied when writing this post. "
            "Useful for auditing and onboarding new team members."
        ),
    )


class WrittenContentBatch(BaseModel):
    # A batch of fully-written posts for the entire week.
    # 
    # WHY a batch model?
    # - The Reviewer Agent (Module 7) receives the ENTIRE week's content at once
    #   so it can check for consistency, repetition, and brand coherence across posts.
    # - The Publisher Agent (Module 9) can then iterate over this batch to schedule each post.

    research_topic: str = Field(
        ...,
        description="The original research topic, carried through the pipeline for traceability.",
    )
    brand_voice: str = Field(
        ...,
        description="The brand voice setting used to write this batch.",
    )
    posts: List[WrittenPost] = Field(
        ...,
        description="All written posts for the week, ready for review.",
    )
