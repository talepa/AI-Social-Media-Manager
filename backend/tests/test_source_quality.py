"""
Tests for source junk / relevance filtering.
"""

from app.schemas.investigation import SourceRecord
from app.services.source_quality import filter_sources, is_junk_text, relevance_score


def _src(id: str, title: str, content: str) -> SourceRecord:
    return SourceRecord(
        id=id,
        type="web",
        title=title,
        url=f"https://example.com/{id}",
        content=content,
        specialist="web",
        sub_question_id="Q1",
    )


def test_junk_nav_menu_detected():
    junk = (
        "AILead ManagementInvoicingSocial MediaProject ManagementData "
        "Management AI AutomationsFor Developers"
    )
    assert is_junk_text(junk) is True


def test_filter_keeps_on_topic_drops_junk():
    query = "difference between loop engineering and prompt engineering"
    sources = [
        _src(
            "WEB-001",
            "What is Prompt Engineering?",
            "Prompt engineering is the practice of crafting inputs to guide LLMs.",
        ),
        _src(
            "WEB-002",
            "What is Loop Engineering?",
            "Loop engineering focuses on outcome loops rather than step prompts.",
        ),
        _src(
            "WEB-003",
            "Reliability Engineering 101",
            "Reliability engineering helps organizations produce more reliable products.",
        ),
        _src(
            "WEB-004",
            "Latenode",
            "AILead ManagementInvoicingSocial MediaProject ManagementData Management",
        ),
    ]
    kept = filter_sources(query, sources, limit=5, min_score=0.15)
    ids = {s.id for s in kept}
    assert "WEB-001" in ids
    assert "WEB-002" in ids
    assert "WEB-004" not in ids
    # Off-topic reliability should score lower / often drop
    assert relevance_score(query, title=sources[2].title, content=sources[2].content) < 0.45
