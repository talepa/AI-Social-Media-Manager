"""
services/report_export.py

Export a ResearchReport to Markdown / printable HTML (for Save as PDF).
"""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.research import ResearchReport


def report_to_markdown(report: "ResearchReport") -> str:
    lines: list[str] = [
        f"# Research report: {report.topic}",
        "",
        f"_Mode: {report.mode}_",
        "",
        "## 1. Executive summary",
        "",
        report.executive_summary.strip(),
        "",
        "## 2. Key findings",
        "",
    ]
    for f in report.key_findings:
        lines.append(f"### {f.rank}. {f.title}")
        lines.append("")
        lines.append(f.summary.strip())
        if f.why_it_matters:
            lines.append("")
            lines.append(f"**Why it matters:** {f.why_it_matters}")
        if f.source_urls:
            lines.append("")
            lines.append("Sources: " + ", ".join(f"<{u}>" for u in f.source_urls))
        lines.append("")

    lines.extend(["## 3. What’s new / in the news", ""])
    if not report.news_highlights:
        lines.append("_No news highlights._")
        lines.append("")
    for n in report.news_highlights:
        lines.append(f"- **[{n.headline}]({n.url})** — {n.summary}")
        lines.append("")

    lines.extend(["## 4. Academic / deeper context", ""])
    if not report.academic_context:
        lines.append("_No academic sources._")
        lines.append("")
    for a in report.academic_context:
        meta = " · ".join(
            x
            for x in [
                ", ".join((a.authors or [])[:3]) or None,
                a.venue,
                f"{a.citation_count} citations" if a.citation_count is not None else None,
            ]
            if x
        )
        lines.append(f"- **[{a.title}]({a.url})**" + (f" — {meta}" if meta else ""))
        lines.append(f"  {a.summary}")
        lines.append("")

    lines.extend(["## 5. Open questions / gaps", ""])
    for q in report.open_questions:
        lines.append(f"- {q}")
    lines.append("")

    if report.media_urls:
        lines.extend(["## Media", ""])
        for url in report.media_urls:
            lines.append(f"![figure]({url})")
            lines.append("")

    lines.extend(["## 6. Sources", ""])
    for i, s in enumerate(report.sources, start=1):
        note = f" — {s.note}" if s.note else ""
        lines.append(f"{i}. [{s.title}]({s.url}) ({s.source}){note}")

    lines.append("")
    return "\n".join(lines)


def report_to_html(report: "ResearchReport") -> str:
    """Printable HTML document — open in browser and Save as PDF / Print."""
    mdish = report_to_markdown(report)
    # Simple structured HTML rather than full markdown parse
    sections: list[str] = []

    def p_block(text: str) -> str:
        paras = [f"<p>{escape(p.strip())}</p>" for p in text.split("\n\n") if p.strip()]
        return "\n".join(paras)

    sections.append(f"<h1>Research report: {escape(report.topic)}</h1>")
    sections.append(f"<p class='meta'>Mode: {escape(report.mode)}</p>")

    if report.stats:
        sections.append(
            "<div class='stats'>"
            f"<span>Web {report.stats.web}</span>"
            f"<span>News {report.stats.news}</span>"
            f"<span>Papers {report.stats.papers}</span>"
            f"<span>Total {report.stats.total}</span>"
            "</div>"
        )

    sections.append("<h2>1. Executive summary</h2>")
    sections.append(p_block(report.executive_summary))

    sections.append("<h2>2. Key findings</h2>")
    for f in report.key_findings:
        sections.append(f"<h3>{f.rank}. {escape(f.title)}</h3>")
        sections.append(f"<p>{escape(f.summary)}</p>")
        if f.why_it_matters:
            sections.append(f"<p><em>Why it matters:</em> {escape(f.why_it_matters)}</p>")
        if f.image_url:
            sections.append(
                f"<img src='{escape(f.image_url)}' alt='' class='fig' />"
            )
        if f.source_urls:
            links = " · ".join(
                f"<a href='{escape(u)}'>{escape(u)}</a>" for u in f.source_urls
            )
            sections.append(f"<p class='srcs'>{links}</p>")

    sections.append("<h2>3. What’s new / in the news</h2>")
    if not report.news_highlights:
        sections.append("<p><em>No news highlights.</em></p>")
    for n in report.news_highlights:
        sections.append(
            f"<p><strong><a href='{escape(n.url)}'>{escape(n.headline)}</a></strong>"
            f" — {escape(n.summary)}</p>"
        )
        if n.image_url:
            sections.append(f"<img src='{escape(n.image_url)}' alt='' class='fig' />")

    sections.append("<h2>4. Academic / deeper context</h2>")
    if not report.academic_context:
        sections.append("<p><em>No academic sources.</em></p>")
    for a in report.academic_context:
        sections.append(
            f"<p><strong><a href='{escape(a.url)}'>{escape(a.title)}</a></strong>"
            f"<br/>{escape(a.summary)}</p>"
        )

    sections.append("<h2>5. Open questions / gaps</h2><ul>")
    for q in report.open_questions:
        sections.append(f"<li>{escape(q)}</li>")
    sections.append("</ul>")

    if report.media_urls:
        sections.append("<h2>Media gallery</h2><div class='gallery'>")
        for url in report.media_urls:
            sections.append(f"<img src='{escape(url)}' alt='' />")
        sections.append("</div>")

    sections.append("<h2>6. Sources</h2><ol>")
    for s in report.sources:
        note = f" — {escape(s.note)}" if s.note else ""
        sections.append(
            f"<li><a href='{escape(s.url)}'>{escape(s.title)}</a> "
            f"({escape(s.source)}){note}</li>"
        )
    sections.append("</ol>")

    body = "\n".join(sections)
    # mdish unused except as fallback reference — keep lint clean
    _ = mdish

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Research report — {escape(report.topic)}</title>
  <style>
    body {{ font-family: Georgia, 'Times New Roman', serif; max-width: 720px;
           margin: 2rem auto; padding: 0 1.25rem; color: #111; line-height: 1.55; }}
    h1, h2, h3 {{ font-weight: 600; letter-spacing: -0.02em; }}
    h1 {{ font-size: 1.85rem; }}
    h2 {{ font-size: 1.25rem; margin-top: 2rem; border-bottom: 1px solid #222; padding-bottom: 0.35rem; }}
    .meta {{ color: #666; font-size: 0.9rem; }}
    .stats {{ display: flex; gap: 1rem; flex-wrap: wrap; margin: 1rem 0; font-size: 0.85rem; }}
    .stats span {{ border: 1px solid #222; padding: 0.35rem 0.65rem; }}
    .fig, .gallery img {{ max-width: 100%; height: auto; margin: 0.75rem 0; border: 1px solid #ddd; }}
    .gallery {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 0.5rem; }}
    .srcs {{ font-size: 0.8rem; word-break: break-all; }}
    a {{ color: #111; }}
    @media print {{
      body {{ margin: 0; max-width: none; }}
      a {{ text-decoration: none; }}
    }}
  </style>
</head>
<body>
{body}
<script>window.addEventListener('load', () => {{ /* ready for print */ }});</script>
</body>
</html>"""
