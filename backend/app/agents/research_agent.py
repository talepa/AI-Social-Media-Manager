"""
agents/research_agent.py

Module 4: Research Agent

RESPONSIBILITY: Research a given topic using available tools and return a
structured ResearchReport. Uses Google Gemini via LangChain's tool-calling
and structured output features.
"""

from typing import List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate

from app.config import get_llm
from app.tools.tavily import tavily_search
from app.tools.google_trends import get_google_trends
from app.tools.reddit import search_reddit
from app.tools.news import fetch_news


# ==========================================
# 1. Structured Output Schema
# ==========================================
class ResearchReport(BaseModel):
    # Pydantic model defining the expected structured output from the Research Agent.
    # This ensures Gemini returns data in a predictable format for the Planner Agent.
    topic: str = Field(..., description="The main topic being researched")
    key_trends: List[str] = Field(..., description="Top 3-5 trends currently popular related to the topic")
    audience_sentiment: str = Field(..., description="Overall sentiment of the target audience on social media")
    recent_news: List[str] = Field(..., description="Summary of 2-3 recent developments or news related to the topic")
    potential_angles: List[str] = Field(..., description="3-5 suggested content angles based on the research")


# ==========================================
# 2. Tools Array
# ==========================================
# Defined for when full tool-calling is wired with real API keys for each tool.
# Currently the tools are stubs — Gemini will use its own knowledge instead.
RESEARCH_TOOLS = [
    tavily_search,
    get_google_trends,
    search_reddit,
    fetch_news,
]


# ==========================================
# 3. Prompt
# ==========================================
RESEARCH_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert social media researcher and trend analyst.
        
Your task is to research a given topic and produce a comprehensive research report
that will be used by a content planning team to create social media posts.

Focus on:
- Current trends and what's gaining traction right now
- Audience sentiment (how people feel about this topic on social media)
- Recent news, launches, or developments (within the last few months)
- Interesting content angles that would perform well on LinkedIn, Instagram, and Twitter

Be specific, insightful, and actionable. Avoid generic observations.
""",
    ),
    (
        "human",
        "Research this topic thoroughly and return a structured report:\n\nTopic: {topic}",
    ),
])


# ==========================================
# 4. Agent Runner
# ==========================================
def run_research_agent(topic: str) -> ResearchReport:
    # Executes the Research Agent using Google Gemini.
    # Uses Gemini's structured output feature to enforce the ResearchReport schema.
    # The LLM cannot return plain prose — it must return validated JSON matching
    # the Pydantic model, which Pydantic then validates automatically.
    # 
    # Args:
    #     topic: The topic/niche to research.
    # 
    # Returns:
    #     A validated ResearchReport Pydantic model.
    # Temperature 0.3 for research — we want factual, consistent output
    llm = get_llm(temperature=0.3)

    # with_structured_output tells Gemini to use function calling / JSON mode
    # to return output that exactly matches the ResearchReport Pydantic schema.
    structured_llm = llm.with_structured_output(ResearchReport)

    chain = RESEARCH_PROMPT | structured_llm

    return chain.invoke({"topic": topic})
