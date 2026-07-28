"""
agents/planner_agent.py

Module 5: Planner Agent

RESPONSIBILITY: Transform a ResearchReport (from the Research Agent) into a
structured WeeklyContentPlan using an LLM with enforced structured output.

WHY structured output?
- The Writer Agent (Module 6) needs a predictable schema to work with.
- Using Pydantic + LLM structured output eliminates the need to manually parse
  LLM text, which is fragile and unreliable.
- Pydantic validation is applied automatically — if the LLM returns invalid data,
  it errors early rather than silently propagating a malformed plan.
"""

from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate

# Import the schemas we just defined in Module 5
from app.schemas.plan import WeeklyContentPlan, PostIdea
# Import the ResearchReport schema from the Research Agent
from app.agents.research_agent import ResearchReport


# ==========================================
# 1. System Prompt
# ==========================================
# WHY this prompt structure?
# - "system" role sets the agent's persona and enforces behavior constraints.
# - "human" role provides the dynamic input (research data).
# - This separation is a LangChain best practice for few-shot and instruction prompts.
PLANNER_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert social media strategist and content planner.
        
Your job is to transform research data into a concrete, actionable weekly content plan.

Rules:
- Create 5-7 post ideas spread across the week (Mon–Fri primarily, Sat for engagement posts).
- Vary platforms: mix LinkedIn (professional insights), Instagram (visual/story), Twitter (quick takes).
- Vary content types: use Educational, Promotional, Engagement, and Storytelling posts.
- Each post idea must be grounded in the research trends and news provided.
- The strategy_summary must explain the WHY behind the week's content approach.
- Target audience should be specific and actionable (e.g., "B2B SaaS founders aged 30-45").
""",
    ),
    (
        "human",
        """Here is the research data for the topic: "{topic}"

Key Trends:
{key_trends}

Audience Sentiment:
{audience_sentiment}

Recent News:
{recent_news}

Potential Content Angles:
{potential_angles}

Based on this research, create a detailed weekly content plan.
""",
    ),
])


# ==========================================
# 2. Planner Agent Runner
# ==========================================
def run_planner_agent(research_report: ResearchReport) -> WeeklyContentPlan:
    """
    Executes the Planner Agent workflow.

    Takes a ResearchReport (output of Research Agent) and produces a
    WeeklyContentPlan with structured, validated post ideas.

    Args:
        research_report: A ResearchReport instance from the Research Agent.

    Returns:
        A WeeklyContentPlan Pydantic model with all fields validated.

    HOW IT WORKS (production):
        1. The prompt is built with research data injected.
        2. The LLM is called with `.with_structured_output(WeeklyContentPlan)`.
        3. LangChain forces the LLM to return JSON that matches the Pydantic schema.
        4. Pydantic validates the JSON — if any field is missing or wrong type, it raises.
    """

    # --- Production Implementation (commented out until LLM keys are configured) ---
    # llm = ChatOpenAI(model="gpt-4-turbo")
    #
    # WHY with_structured_output?
    # This is LangChain's way of enforcing function calling / JSON mode on the LLM.
    # The LLM is instructed to return ONLY valid JSON matching the WeeklyContentPlan schema.
    # structured_llm = llm.with_structured_output(WeeklyContentPlan)
    #
    # chain = PLANNER_PROMPT | structured_llm
    #
    # return chain.invoke({
    #     "topic": research_report.topic,
    #     "key_trends": "\n".join(f"- {t}" for t in research_report.key_trends),
    #     "audience_sentiment": research_report.audience_sentiment,
    #     "recent_news": "\n".join(f"- {n}" for n in research_report.recent_news),
    #     "potential_angles": "\n".join(f"- {a}" for a in research_report.potential_angles),
    # })

    # --- Mock Implementation (for showcase until LLM is wired up) ---
    # WHY mock? To demonstrate the full pipeline structure and validate schemas
    # without requiring a live API key during the build phase.
    return WeeklyContentPlan(
        research_topic=research_report.topic,
        strategy_summary=(
            f"This week's strategy focuses on establishing thought leadership around '{research_report.topic}'. "
            "We lead with educational content early in the week to build credibility, "
            "use mid-week engagement posts to drive interaction, and close with storytelling "
            "content on Friday to humanize the brand."
        ),
        target_audience="B2B professionals, marketers, and founders aged 28-45 interested in AI-driven business tools.",
        post_ideas=[
            PostIdea(
                platform="LinkedIn",
                topic=f"Why {research_report.topic} is changing the industry",
                content_summary=(
                    f"Based on recent trends, {research_report.key_trends[0] if research_report.key_trends else 'AI advancements'} "
                    "are reshaping how professionals work. Here's what you need to know to stay ahead. "
                    "Link to our in-depth guide in the comments."
                ),
                suggested_publish_day="Monday",
                content_type="Educational",
            ),
            PostIdea(
                platform="Twitter",
                topic=f"Hot take: {research_report.topic}",
                content_summary=(
                    f"The audience sentiment around {research_report.topic} is '{research_report.audience_sentiment}'. "
                    "We share a bold 3-point take to spark discussion and drive retweets."
                ),
                suggested_publish_day="Tuesday",
                content_type="Engagement",
            ),
            PostIdea(
                platform="Instagram",
                topic=f"Behind the trend: {research_report.topic}",
                content_summary=(
                    "A visually rich carousel post breaking down the top trends in an easy-to-digest format. "
                    f"Highlights: {', '.join(research_report.key_trends[:2]) if research_report.key_trends else 'key insights'}."
                ),
                suggested_publish_day="Wednesday",
                content_type="Educational",
            ),
            PostIdea(
                platform="LinkedIn",
                topic=f"News Roundup: What happened in {research_report.topic} this week",
                content_summary=(
                    f"Covering key developments: {research_report.recent_news[0] if research_report.recent_news else 'latest updates'}. "
                    "We add our expert commentary on what this means for businesses."
                ),
                suggested_publish_day="Thursday",
                content_type="Storytelling",
            ),
            PostIdea(
                platform="Instagram",
                topic="Community question: How are YOU adapting?",
                content_summary=(
                    f"An engagement-first post asking followers how they are adapting to changes in {research_report.topic}. "
                    "Uses a poll sticker and an open-ended question to maximize story interactions."
                ),
                suggested_publish_day="Friday",
                content_type="Engagement",
            ),
        ],
    )
