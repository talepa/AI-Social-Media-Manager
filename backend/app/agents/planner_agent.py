"""
agents/planner_agent.py

Module 5: Planner Agent

RESPONSIBILITY: Transform a ResearchReport into a structured WeeklyContentPlan
using Google Gemini with enforced structured output.
"""

from langchain_core.prompts import ChatPromptTemplate

from app.config import get_llm
from app.schemas.plan import WeeklyContentPlan
from app.agents.research_agent import ResearchReport


# ==========================================
# 1. Prompt
# ==========================================
# WHY two-message structure?
# - "system" sets the planner's persona and hard rules once.
# - "human" provides the dynamic research data per invocation.
# This separation also enables prompt caching on the LLM API side.
PLANNER_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert social media strategist and content planner with 10 years of experience.

Your job is to transform research data into a concrete, actionable weekly content plan.

Rules you MUST follow:
- Create exactly 5 post ideas spread across Monday–Friday (one per day).
- Vary platforms across the week: mix LinkedIn, Instagram, and Twitter.
- Vary content types: use Educational, Promotional, Engagement, and Storytelling.
- Every post idea must be directly grounded in the research data provided.
- The strategy_summary must be 2-3 sentences explaining the WHY behind the week's approach.
- target_audience must be specific (e.g. "B2B SaaS founders aged 30-45, interested in AI tools").
- Each content_summary should be 2-3 sentences describing exactly what the post should convey.
""",
    ),
    (
        "human",
        """Create a weekly content plan based on this research:

Topic: {topic}

Key Trends:
{key_trends}

Audience Sentiment: {audience_sentiment}

Recent News:
{recent_news}

Potential Content Angles:
{potential_angles}

Now create a detailed weekly content plan with 5 posts (Mon–Fri).
""",
    ),
])


# ==========================================
# 2. Agent Runner
# ==========================================
def run_planner_agent(research_report: ResearchReport) -> WeeklyContentPlan:
    # Executes the Planner Agent using Google Gemini.
    # 
    # Takes a ResearchReport and produces a WeeklyContentPlan with structured,
    # validated post ideas. Gemini's structured output enforces the Pydantic schema —
    # if any field is missing or the wrong type, it raises a validation error immediately.
    # 
    # Args:
    #     research_report: A ResearchReport instance from the Research Agent.
    # 
    # Returns:
    #     A validated WeeklyContentPlan Pydantic model.
    # Temperature 0.5 — balanced: creative enough for good ideas, consistent for structure
    llm = get_llm(temperature=0.5)
    structured_llm = llm.with_structured_output(WeeklyContentPlan)

    chain = PLANNER_PROMPT | structured_llm

    return chain.invoke({
        "topic": research_report.topic,
        "key_trends": "\n".join(f"- {t}" for t in research_report.key_trends),
        "audience_sentiment": research_report.audience_sentiment,
        "recent_news": "\n".join(f"- {n}" for n in research_report.recent_news),
        "potential_angles": "\n".join(f"- {a}" for a in research_report.potential_angles),
    })
