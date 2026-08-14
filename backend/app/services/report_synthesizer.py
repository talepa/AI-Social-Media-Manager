"""
services/report_synthesizer.py

Compile a structured research report from multi-source findings.
Optional Gemini enhancement when use_llm=True.
"""

from __future__ import annotations

import json
import logging
from typing import List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.config import get_llm
from app.schemas.research import (
    AcademicInsight,
    MultiSourceResearchResult,
    NewsHighlight,
    RankedFinding,
    ReportSource,
    ReportStats,
    ResearchItem,
    ResearchReport,
)

logger = logging.getLogger(__name__)

_SNIPPET_MAX = 420
_MAX_ITEMS_PER_SOURCE = 8


def _clip(text: str, n: int = _SNIPPET_MAX) -> str:
    text = (text or "").strip()
    if len(text) <= n:
        return text
    return text[: n - 1].rstrip() + "…"


def _collect_media(result: MultiSourceResearchResult) -> List[str]:
    urls: List[str] = []
    seen = set()
    for u in result.media_urls or []:
        if u and u not in seen:
            seen.add(u)
            urls.append(u)
    for item in [
        *result.tavily_results,
        *result.news_results,
        *result.papers_results,
    ]:
        if item.image_url and item.image_url not in seen:
            seen.add(item.image_url)
            urls.append(item.image_url)
    return urls[:16]


def _stats(result: MultiSourceResearchResult) -> ReportStats:
    web = len(result.tavily_results)
    news = len(result.news_results)
    papers = len(result.papers_results)
    return ReportStats(web=web, news=news, papers=papers, total=web + news + papers)


def _item_payload(item: ResearchItem) -> dict:
    return {
        "title": item.title,
        "url": item.url,
        "source": item.source,
        "snippet": _clip(item.content),
        "score": item.score,
        "published": item.published,
        "authors": (item.authors or [])[:4] or None,
        "venue": item.venue,
        "citation_count": item.citation_count,
        "image_url": item.image_url,
    }


def _build_corpus(result: MultiSourceResearchResult) -> dict:
    return {
        "topic": result.topic,
        "tavily_answer": result.tavily_answer,
        "web": [_item_payload(i) for i in result.tavily_results[:_MAX_ITEMS_PER_SOURCE]],
        "news": [_item_payload(i) for i in result.news_results[:_MAX_ITEMS_PER_SOURCE]],
        "papers": [
            _item_payload(i) for i in result.papers_results[:_MAX_ITEMS_PER_SOURCE]
        ],
        "media_urls": _collect_media(result),
        "source_errors": result.errors or {},
    }


_SYSTEM = """You are a senior research analyst writing a clear, evidence-based briefing.

Ground every claim in the provided sources. Do not invent URLs, titles, authors, or citations.
If evidence is thin, say so in open_questions rather than fabricating findings.
Prefer concrete, attributable statements over vague marketing language.
Use only URLs that appear in the source corpus.
Write executive_summary as 2–4 short paragraphs separated by blank lines.
Rank key_findings by importance (rank 1 = most important), typically 4–7 items.
You may set image_url on a finding only if that exact URL appears in the corpus.
news_highlights should emphasize timely coverage from the news list.
academic_context should emphasize papers / deeper evidence.
open_questions should list genuine gaps, contradictions, or follow-ups (3–6).
sources should be a de-duplicated bibliography of the URLs you actually used, with short notes.
Set mode to "llm". Leave stats null (server will fill). media_urls may copy from corpus.
"""


def _rank_key(item: ResearchItem) -> tuple:
    score = item.score if item.score is not None else -1.0
    cites = item.citation_count if item.citation_count is not None else -1
    return (score, cites)


def compile_report(result: MultiSourceResearchResult) -> ResearchReport:
    """Deterministic, no-LLM report from retrieved sources."""
    ranked_web = sorted(result.tavily_results, key=_rank_key, reverse=True)
    ranked_papers = sorted(result.papers_results, key=_rank_key, reverse=True)

    mixed: List[ResearchItem] = []
    for bucket in (ranked_web[:4], result.news_results[:2], ranked_papers[:2]):
        for item in bucket:
            if item not in mixed:
                mixed.append(item)

    findings: List[RankedFinding] = []
    for i, item in enumerate(mixed[:7], start=1):
        findings.append(
            RankedFinding(
                rank=i,
                title=item.title,
                summary=_clip(item.content, 280) or "See source for details.",
                why_it_matters=f"Ranked from {item.source} evidence for this topic.",
                source_urls=[item.url],
                source_types=[item.source],
                image_url=item.image_url,
            )
        )

    news = [
        NewsHighlight(
            headline=n.title,
            summary=_clip(n.content, 240) or n.title,
            url=n.url,
            published=n.published,
            image_url=n.image_url,
        )
        for n in result.news_results[:6]
    ]
    academic = [
        AcademicInsight(
            title=p.title,
            summary=_clip(p.content, 280) or p.title,
            url=p.url,
            authors=p.authors,
            venue=p.venue,
            citation_count=p.citation_count,
        )
        for p in ranked_papers[:6]
    ]

    sources: List[ReportSource] = []
    seen = set()
    for item in [
        *result.tavily_results,
        *result.news_results,
        *result.papers_results,
    ]:
        if item.url in seen:
            continue
        seen.add(item.url)
        sources.append(
            ReportSource(
                title=item.title,
                url=item.url,
                source=item.source,
                note=_clip(item.content, 120) or None,
                image_url=item.image_url,
            )
        )

    stats = _stats(result)
    summary_bits = [
        f'This briefing compiles {stats.total} sources on “{result.topic}” '
        f"({stats.web} web, {stats.news} news, {stats.papers} papers).",
    ]
    if result.tavily_answer:
        summary_bits.append(result.tavily_answer.strip())
    else:
        summary_bits.append(
            "Findings below are ranked from retrieved titles, snippets, scores, "
            "and citation signals — no generative rewrite was applied."
        )

    open_q = [
        "Which claims need primary-source verification?",
        "What recent developments are missing from this sample?",
        "Where do web, news, and papers disagree?",
    ]
    if stats.papers == 0:
        open_q.insert(0, "No academic papers were retrieved — is the topic too industry-specific?")
    if stats.news == 0:
        open_q.insert(0, "No news headlines matched — try a more timely framing of the topic.")

    return ResearchReport(
        topic=result.topic,
        executive_summary="\n\n".join(summary_bits),
        key_findings=findings,
        news_highlights=news,
        academic_context=academic,
        open_questions=open_q[:6],
        sources=sources[:40],
        media_urls=_collect_media(result),
        stats=stats,
        mode="compile",
    )


def synthesize_report(
    result: MultiSourceResearchResult,
    *,
    use_llm: bool = False,
) -> tuple[Optional[ResearchReport], Optional[str]]:
    """
    Returns (report, error).
    Default is deterministic compile. When use_llm=True, Gemini enhances;
    on LLM failure, falls back to compile and returns the error string.
    """
    total = (
        len(result.tavily_results)
        + len(result.news_results)
        + len(result.papers_results)
    )
    if total == 0:
        return None, "No sources available to synthesize a report."

    if not use_llm:
        return compile_report(result), None

    corpus = _build_corpus(result)
    prompt = (
        "Produce a ResearchReport JSON for this topic using ONLY the corpus below.\n\n"
        f"CORPUS:\n{json.dumps(corpus, ensure_ascii=False, indent=2)}"
    )

    try:
        llm = get_llm(temperature=0.25)
        structured = llm.with_structured_output(ResearchReport)
        report = structured.invoke(
            [
                SystemMessage(content=_SYSTEM),
                HumanMessage(content=prompt),
            ]
        )
        if not isinstance(report, ResearchReport):
            report = ResearchReport.model_validate(report)
        if not report.topic:
            report.topic = result.topic
        report.mode = "llm"
        report.stats = _stats(result)
        if not report.media_urls:
            report.media_urls = _collect_media(result)
        return report, None
    except Exception as exc:
        logger.exception("Report LLM synthesis failed; using compile fallback")
        return compile_report(result), str(exc)
