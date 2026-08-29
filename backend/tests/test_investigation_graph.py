"""
Unit tests for the investigation graph specialists phase (budget split,
aggregation, dispatch).
"""

from app.graphs.investigation_graph import (
    _aggregate_results,
    _allocate_budgets,
    specialists_node,
)
from app.schemas.investigation import (
    InvestigationPlan,
    ResearchFinding,
    SourceRecord,
    SpecialistResult,
    SubQuestion,
)


def test_allocate_budgets_splits_evenly():
    plan = InvestigationPlan(
        objective="Test",
        mode="explore",
        depth="standard",
        sub_questions=[
            SubQuestion(id="Q1", text="a", specialist="web"),
            SubQuestion(id="Q2", text="b", specialist="repository"),
            SubQuestion(id="Q3", text="c", specialist="web"),
        ],
        tool_budget=12,
        max_tasks=5,
    )
    budgets = _allocate_budgets(plan)
    assert sum(budgets.values()) == 12
    assert all(v >= 1 for v in budgets.values())


def test_allocate_budgets_quick_depth():
    plan = InvestigationPlan(
        objective="Test",
        mode="explore",
        depth="quick",
        sub_questions=[
            SubQuestion(id="Q1", text="a", specialist="web"),
            SubQuestion(id="Q2", text="b", specialist="web"),
        ],
        tool_budget=6,
        max_tasks=3,
    )
    budgets = _allocate_budgets(plan)
    assert sum(budgets.values()) == 6


def test_aggregate_results_rewrites_ids():
    r1 = SpecialistResult(
        specialist="web",
        sub_question_id="Q1",
        sources=[
            SourceRecord(
                id="WEB-001",
                type="web",
                title="A",
                url="https://a.example",
                specialist="web",
                sub_question_id="Q1",
            )
        ],
        findings=[
            ResearchFinding(
                id="F-001",
                sub_question_id="Q1",
                specialist="web",
                claim="Claim A",
                source_ids=["WEB-001"],
                confidence=0.8,
            )
        ],
    )
    r2 = SpecialistResult(
        specialist="web",
        sub_question_id="Q2",
        sources=[
            SourceRecord(
                id="WEB-001",
                type="web",
                title="B",
                url="https://b.example",
                specialist="web",
                sub_question_id="Q2",
            )
        ],
        findings=[
            ResearchFinding(
                id="F-001",
                sub_question_id="Q2",
                specialist="web",
                claim="Claim B",
                source_ids=["WEB-001"],
                confidence=0.6,
            )
        ],
    )
    sources, findings, rewritten = _aggregate_results([r1, r2])
    assert [s.id for s in sources] == ["WEB-001", "WEB-002"]
    assert [f.id for f in findings] == ["F-001", "F-002"]
    assert findings[0].source_ids == ["WEB-001"]
    assert findings[1].source_ids == ["WEB-002"]
    assert rewritten[1].sources[0].id == "WEB-002"


def test_specialists_node_dispatches(monkeypatch):
    calls: list[str] = []

    def fake_run(sq: SubQuestion, *, max_tool_calls: int = 1) -> SpecialistResult:
        calls.append(sq.id)
        return SpecialistResult(
            specialist=sq.specialist,
            sub_question_id=sq.id,
            sources=[
                SourceRecord(
                    id="WEB-001",
                    type="web",
                    title="t",
                    url="https://example.com",
                    specialist=sq.specialist,
                    sub_question_id=sq.id,
                )
            ],
            findings=[
                ResearchFinding(
                    id="F-001",
                    sub_question_id=sq.id,
                    specialist=sq.specialist,
                    claim="c",
                    source_ids=["WEB-001"],
                    confidence=0.5,
                )
            ],
            tool_calls_used=1,
            llm_calls_used=1,
        )

    monkeypatch.setattr(
        "app.graphs.investigation_graph.run_for_sub_question",
        fake_run,
    )

    plan = InvestigationPlan(
        objective="Test",
        mode="explore",
        depth="quick",
        sub_questions=[
            SubQuestion(id="Q1", text="one", specialist="web"),
            SubQuestion(id="Q2", text="two", specialist="repository"),
        ],
        required_specialists=["web", "repository"],
        tool_budget=6,
        max_tasks=3,
    )
    out = specialists_node(
        {
            "run_id": "run-1",
            "question": "test",
            "mode": "explore",
            "depth": "quick",
            "plan": plan.model_dump(mode="json"),
            "tool_calls_used": 1,
            "llm_calls_used": 1,
            "errors": {},
            "events": [],
        }
    )
    assert set(calls) == {"Q1", "Q2"}
    assert len(out["specialist_results"]) == 2
    assert {s["id"] for s in out["sources"]} == {"WEB-001", "GH-001"}
    assert out["tool_calls_used"] == 3  # prior 1 + 2 from specialists
    assert out["events"][0]["event_type"] == "specialists_completed"
