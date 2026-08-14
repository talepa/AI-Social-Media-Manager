"""
graphs/sample_graph.py

Module 3: LangGraph pipeline for Modules 4-6.

The API starts a run and returns the final state. ContentPipelineState is the
contract between nodes. Later modules (reviewer loops, human approval,
checkpointer) attach here as extra nodes/edges without rewriting FastAPI.

Flow: START -> research -> planner -> writer -> END
"""

from typing import NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.planner_agent import run_planner_agent
from app.agents.research_agent import ResearchReport, run_research_agent
from app.agents.writer_agent import run_writer_agent
from app.schemas.content import WrittenContentBatch
from app.schemas.plan import WeeklyContentPlan


class ContentPipelineState(TypedDict):
    # Shared bag of data passed between nodes.
    # Each node returns only the keys it updates; LangGraph merges them.
    # topic / brand_voice are required inputs. The rest are filled as the
    # graph runs, so they are NotRequired on the initial invoke.
    topic: str
    brand_voice: str
    research_report: NotRequired[ResearchReport]
    content_plan: NotRequired[WeeklyContentPlan]
    written_content: NotRequired[WrittenContentBatch]


def research_node(state: ContentPipelineState) -> dict:
    # Module 4: produce a ResearchReport from the topic.
    report = run_research_agent(topic=state["topic"])
    return {"research_report": report}


def planner_node(state: ContentPipelineState) -> dict:
    # Module 5: turn research into a weekly content plan.
    research_report = state.get("research_report")
    if research_report is None:
        raise ValueError("planner_node requires research_report from the research node")
    if isinstance(research_report, dict):
        research_report = ResearchReport.model_validate(research_report)
    plan = run_planner_agent(research_report=research_report)
    return {"content_plan": plan}


def writer_node(state: ContentPipelineState) -> dict:
    # Module 6: write one platform-specific post per planned idea.
    content_plan = state.get("content_plan")
    if content_plan is None:
        raise ValueError("writer_node requires content_plan from the planner node")
    if isinstance(content_plan, dict):
        content_plan = WeeklyContentPlan.model_validate(content_plan)
    batch = run_writer_agent(
        content_plan=content_plan,
        brand_voice=state.get("brand_voice", "professional"),
    )
    return {"written_content": batch}


def build_content_graph():
    # Compiling produces a Runnable the API can invoke with {topic, brand_voice}.
    workflow = StateGraph(ContentPipelineState)

    workflow.add_node("research", research_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("writer", writer_node)

    workflow.add_edge(START, "research")
    workflow.add_edge("research", "planner")
    workflow.add_edge("planner", "writer")
    workflow.add_edge("writer", END)

    return workflow.compile()


content_graph = build_content_graph()

# Alias kept so Module 3's original `graph` name still works if imported.
graph = content_graph
