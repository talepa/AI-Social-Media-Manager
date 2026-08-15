"use client";

/**
 * Interactive research product UI:
 * Hero → Research studio → Loader → Report + sources
 */

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import HeroHome from "../components/HeroHome";
import {
  downloadReportJson,
  downloadReportMarkdown,
  openReportPrintPdf,
} from "../lib/reportDownload";

const API_BASE = "http://localhost:8001";

type View = "hero" | "studio" | "loading" | "results";
type SourceKey = "tavily" | "news" | "papers" | "github";
type ResearchCategory =
  | "general"
  | "ai_engineer"
  | "founder"
  | "academic"
  | "news_desk";
type TabKey = "report" | "overview" | SourceKey;
type LayoutMode = "cards" | "list";

interface ResearchItem {
  title: string;
  url: string;
  content: string;
  source: SourceKey;
  score: number | null;
  published: string | null;
  authors: string[] | null;
  venue: string | null;
  citation_count: number | null;
  image_url?: string | null;
  favicon_url?: string | null;
}

interface RankedFinding {
  rank: number;
  title: string;
  summary: string;
  why_it_matters: string;
  source_urls: string[];
  source_types: SourceKey[];
  image_url?: string | null;
}

interface NewsHighlight {
  headline: string;
  summary: string;
  url: string;
  published: string | null;
  image_url?: string | null;
}

interface AcademicInsight {
  title: string;
  summary: string;
  url: string;
  authors: string[] | null;
  venue: string | null;
  citation_count: number | null;
}

interface ReportSource {
  title: string;
  url: string;
  source: SourceKey;
  note: string | null;
  image_url?: string | null;
}

interface ReportStats {
  web: number;
  news: number;
  papers: number;
  github?: number;
  total: number;
}

interface ResearchReport {
  topic: string;
  executive_summary: string;
  key_findings: RankedFinding[];
  news_highlights: NewsHighlight[];
  academic_context: AcademicInsight[];
  open_questions: string[];
  sources: ReportSource[];
  media_urls: string[];
  stats: ReportStats | null;
  mode: "compile" | "llm";
}

interface MultiSourceResearchResult {
  topic: string;
  category?: string | null;
  sources_used?: SourceKey[];
  tavily_results: ResearchItem[];
  news_results: ResearchItem[];
  papers_results: ResearchItem[];
  github_results?: ResearchItem[];
  tavily_answer: string | null;
  media_urls: string[];
  errors: Record<string, string>;
  report: ResearchReport | null;
  report_error: string | null;
  cached?: boolean;
  cache_key?: string | null;
  fetched_at: string;
}

const SOURCE_META: Record<
  SourceKey,
  { label: string; tool: string; method: string; index: string }
> = {
  tavily: {
    label: "Web",
    tool: "Tavily Search",
    method: "Live web search — ranked pages with titles, links, and snippets.",
    index: "01",
  },
  news: {
    label: "News",
    tool: "Google News RSS",
    method: "Fresh headlines from public news feeds — timely coverage.",
    index: "02",
  },
  papers: {
    label: "Papers",
    tool: "S2 · OpenAlex · Crossref · arXiv",
    method: "Academic libraries in parallel — merged and deduped by title/DOI.",
    index: "03",
  },
  github: {
    label: "GitHub",
    tool: "GitHub Search API",
    method: "Public repositories ranked by stars — code, tools, and reference implementations.",
    index: "04",
  },
};

const CATEGORIES: {
  id: ResearchCategory;
  label: string;
  blurb: string;
  sources: SourceKey[];
  examples: string[];
}[] = [
  {
    id: "general",
    label: "General",
    blurb: "Web, news, and papers",
    sources: ["tavily", "news", "papers"],
    examples: [
      "AI agents for founders",
      "LinkedIn thought leadership 2026",
      "Climate tech funding news",
    ],
  },
  {
    id: "ai_engineer",
    label: "AI Engineer",
    blurb: "Web, papers, and GitHub repos",
    sources: ["tavily", "papers", "github"],
    examples: [
      "LangGraph multi-agent orchestration",
      "RAG evaluation benchmarks",
      "vLLM inference optimization",
    ],
  },
  {
    id: "founder",
    label: "Founder",
    blurb: "Web, news, and papers",
    sources: ["tavily", "news", "papers"],
    examples: [
      "B2B SaaS pricing 2026",
      "PLG onboarding patterns",
      "AI startup fundraising news",
    ],
  },
  {
    id: "academic",
    label: "Academic",
    blurb: "Papers first, then web",
    sources: ["papers", "tavily"],
    examples: [
      "Transformer attention mechanisms",
      "Diffusion model sampling",
      "Causal inference in ML",
    ],
  },
  {
    id: "news_desk",
    label: "News desk",
    blurb: "News and web only",
    sources: ["news", "tavily"],
    examples: [
      "OpenAI product launches",
      "EU AI Act enforcement",
      "Chip export controls 2026",
    ],
  },
];

const CAPABILITIES = [
  {
    title: "Research topics",
    body: "Pull live context from the open web before you draft a word.",
  },
  {
    title: "Read the news",
    body: "Surface what’s trending today so the report stays timely.",
  },
  {
    title: "Scan articles & papers",
    body: "Ground ideas in journalism and academic sources, not guesses.",
  },
  {
    title: "Get a full report",
    body: "Executive summary, ranked findings, gaps, and a source list.",
  },
] as const;

const LOAD_STAGES = [
  { label: "Scanning the web", tool: "Tavily" },
  { label: "Collecting headlines", tool: "Google News" },
  { label: "Reading papers", tool: "OpenAlex / S2" },
  { label: "Searching GitHub", tool: "Repos" },
  { label: "Organising findings", tool: "LangGraph" },
];

const SOURCE_TAB_ORDER: TabKey[] = [
  "overview",
  "tavily",
  "news",
  "papers",
  "github",
];

function hostnameOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function ReportSection({
  index,
  title,
  children,
}: {
  index: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <section style={{ marginBottom: "2.5rem" }}>
      <p
        style={{
          margin: 0,
          fontSize: "0.66rem",
          letterSpacing: "0.16em",
          textTransform: "uppercase",
          color: "var(--muted)",
        }}
      >
        {index}
      </p>
      <h3
        style={{
          margin: "0.35rem 0 1rem",
          fontFamily: "var(--font-display)",
          fontSize: "clamp(1.55rem, 3vw, 1.95rem)",
          fontWeight: 500,
          letterSpacing: "-0.02em",
        }}
      >
        {title}
      </h3>
      <div className="rule-grow" style={{ height: 1, background: "var(--ink)", marginBottom: "1.15rem" }} />
      {children}
    </section>
  );
}

function SourceMixChart({ stats }: { stats: ReportStats }) {
  const github = stats.github ?? 0;
  const max = Math.max(stats.web, stats.news, stats.papers, github, 1);
  const rows: [string, number][] = [
    ["Web", stats.web],
    ["News", stats.news],
    ["Papers", stats.papers],
  ];
  if (github > 0) rows.push(["GitHub", github]);
  return (
    <div className="source-mix" aria-label="Source mix">
      {rows.map(([label, value]) => (
        <div key={label} className="source-mix-row">
          <span className="source-mix-label">{label}</span>
          <div className="source-mix-track">
            <div
              className="source-mix-fill"
              style={{ width: `${Math.round((value / max) * 100)}%` }}
            />
          </div>
          <span className="source-mix-val">{value}</span>
        </div>
      ))}
    </div>
  );
}

function ResearchReportView({
  report,
  reportError,
  onDownloadMd,
  onDownloadJson,
  onDownloadPdf,
  downloading,
}: {
  report: ResearchReport;
  reportError: string | null;
  onDownloadMd: () => void;
  onDownloadJson: () => void;
  onDownloadPdf: () => void;
  downloading: boolean;
}) {
  return (
    <article className="rise">
      <div className="report-toolbar">
        <p style={{ margin: 0, fontSize: "0.72rem", color: "var(--muted)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
          Mode · {report.mode === "llm" ? "AI enhanced" : "Compiled"}
          {reportError ? " · fallback" : ""}
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
          <button type="button" className="btn-3d-ghost" style={{ padding: "0.55rem 0.85rem" }} disabled={downloading} onClick={onDownloadMd}>
            Markdown
          </button>
          <button type="button" className="btn-3d-ghost" style={{ padding: "0.55rem 0.85rem" }} disabled={downloading} onClick={onDownloadJson}>
            JSON
          </button>
          <button type="button" className="btn-3d" style={{ padding: "0.55rem 0.85rem" }} disabled={downloading} onClick={onDownloadPdf}>
            PDF / Print
          </button>
        </div>
      </div>

      {reportError && (
        <p
          style={{
            margin: "0 0 1.25rem",
            color: "var(--warn)",
            fontSize: "0.85rem",
            borderLeft: "2px solid var(--warn)",
            paddingLeft: "0.75rem",
          }}
        >
          AI enhance had an issue — showing the compiled report instead.
        </p>
      )}

      {report.stats && (
        <ReportSection index="00" title="Source mix">
          <SourceMixChart stats={report.stats} />
        </ReportSection>
      )}

      <ReportSection index="01" title="Executive summary">
        {report.executive_summary.split(/\n\n+/).map((para, i) => (
          <p
            key={i}
            style={{
              margin: i === 0 ? 0 : "1rem 0 0",
              fontSize: "1.05rem",
              lineHeight: 1.7,
              color: "var(--ink-soft)",
              maxWidth: "42rem",
            }}
          >
            {para}
          </p>
        ))}
      </ReportSection>

      <ReportSection index="02" title="Key findings">
        <ol style={{ listStyle: "none", margin: 0, padding: 0 }}>
          {report.key_findings.map((f) => (
            <li
              key={`${f.rank}-${f.title}`}
              style={{
                padding: "1.15rem 0",
                borderBottom: "1px solid var(--line)",
              }}
            >
              <p
                style={{
                  margin: 0,
                  fontSize: "0.66rem",
                  letterSpacing: "0.14em",
                  textTransform: "uppercase",
                  color: "var(--muted)",
                }}
              >
                Finding {String(f.rank).padStart(2, "0")}
                {f.source_types?.length ? ` · ${f.source_types.join(" · ")}` : ""}
              </p>
              <p
                style={{
                  margin: "0.4rem 0 0",
                  fontFamily: "var(--font-display)",
                  fontSize: "1.35rem",
                  fontWeight: 500,
                  lineHeight: 1.25,
                }}
              >
                {f.title}
              </p>
              {f.image_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={f.image_url} alt="" className="report-fig" />
              ) : null}
              <p style={{ margin: "0.55rem 0 0", lineHeight: 1.65, color: "var(--ink-soft)", maxWidth: "40rem" }}>
                {f.summary}
              </p>
              {f.why_it_matters ? (
                <p style={{ margin: "0.45rem 0 0", fontSize: "0.88rem", color: "var(--muted)" }}>
                  Why it matters: {f.why_it_matters}
                </p>
              ) : null}
              {f.source_urls?.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.65rem", marginTop: "0.7rem" }}>
                  {f.source_urls.map((u) => (
                    <a
                      key={u}
                      href={u}
                      target="_blank"
                      rel="noreferrer"
                      style={{
                        fontSize: "0.7rem",
                        letterSpacing: "0.08em",
                        textTransform: "uppercase",
                        borderBottom: "1px solid var(--ink)",
                        textDecoration: "none",
                      }}
                    >
                      {hostnameOf(u)}
                    </a>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ol>
      </ReportSection>

      <ReportSection index="03" title="What’s new / in the news">
        {report.news_highlights.length === 0 ? (
          <p style={{ color: "var(--muted)" }}>No news highlights in this run.</p>
        ) : (
          <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
            {report.news_highlights.map((n) => (
              <li
                key={n.url}
                style={{
                  padding: "1rem 0",
                  borderBottom: "1px solid var(--line)",
                }}
              >
                {n.image_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={n.image_url} alt="" className="report-fig" />
                ) : null}
                <a
                  href={n.url}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    fontFamily: "var(--font-display)",
                    fontSize: "1.2rem",
                    fontWeight: 500,
                    textDecoration: "none",
                  }}
                >
                  {n.headline}
                </a>
                {n.published ? (
                  <p style={{ margin: "0.3rem 0 0", fontSize: "0.72rem", color: "var(--muted)" }}>
                    {n.published}
                  </p>
                ) : null}
                <p style={{ margin: "0.45rem 0 0", color: "var(--ink-soft)", lineHeight: 1.6, maxWidth: "40rem" }}>
                  {n.summary}
                </p>
              </li>
            ))}
          </ul>
        )}
      </ReportSection>

      <ReportSection index="04" title="Academic / deeper context">
        {report.academic_context.length === 0 ? (
          <p style={{ color: "var(--muted)" }}>No academic sources in this run.</p>
        ) : (
          <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
            {report.academic_context.map((a) => (
              <li
                key={a.url}
                style={{
                  padding: "1rem 0",
                  borderBottom: "1px solid var(--line)",
                }}
              >
                <a
                  href={a.url}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    fontFamily: "var(--font-display)",
                    fontSize: "1.2rem",
                    fontWeight: 500,
                    textDecoration: "none",
                  }}
                >
                  {a.title}
                </a>
                <p style={{ margin: "0.35rem 0 0", fontSize: "0.75rem", color: "var(--muted)" }}>
                  {[a.authors?.slice(0, 3).join(", "), a.venue, a.citation_count != null ? `${a.citation_count} citations` : null]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
                <p style={{ margin: "0.45rem 0 0", color: "var(--ink-soft)", lineHeight: 1.6, maxWidth: "40rem" }}>
                  {a.summary}
                </p>
              </li>
            ))}
          </ul>
        )}
      </ReportSection>

      <ReportSection index="05" title="Open questions / gaps">
        <ul style={{ margin: 0, paddingLeft: "1.1rem", color: "var(--ink-soft)", lineHeight: 1.7 }}>
          {report.open_questions.map((q) => (
            <li key={q} style={{ marginBottom: "0.45rem" }}>
              {q}
            </li>
          ))}
        </ul>
      </ReportSection>

      <ReportSection index="06" title="Sources">
        <ol style={{ listStyle: "none", margin: 0, padding: 0 }}>
          {report.sources.map((s, i) => (
            <li
              key={`${s.url}-${i}`}
              style={{
                display: "grid",
                gridTemplateColumns: "2.2rem 1fr",
                gap: "0.5rem",
                padding: "0.7rem 0",
                borderBottom: "1px solid var(--line)",
              }}
            >
              <span style={{ color: "var(--muted)", fontSize: "0.75rem" }}>
                {String(i + 1).padStart(2, "0")}
              </span>
              <div>
                <a
                  href={s.url}
                  target="_blank"
                  rel="noreferrer"
                  style={{ textDecoration: "none", borderBottom: "1px solid var(--ink)" }}
                >
                  {s.title}
                </a>
                <p style={{ margin: "0.25rem 0 0", fontSize: "0.72rem", color: "var(--muted)" }}>
                  {s.source} · {hostnameOf(s.url)}
                  {s.note ? ` — ${s.note}` : ""}
                </p>
              </div>
            </li>
          ))}
        </ol>
      </ReportSection>
    </article>
  );
}

function ScoreBars({ items }: { items: ResearchItem[] }) {
  const scored = items
    .filter((i) => i.score != null)
    .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
    .slice(0, 6);
  if (scored.length === 0) return null;
  return (
    <div className="viz-block">
      <p className="viz-label">Relevance scores (web)</p>
      <div className="score-bars">
        {scored.map((i) => (
          <div key={i.url} className="score-bar-row" title={i.title}>
            <span className="score-bar-name">{i.title}</span>
            <div className="score-bar-track">
              <div
                className="score-bar-fill"
                style={{ width: `${Math.round((i.score ?? 0) * 100)}%` }}
              />
            </div>
            <span className="score-bar-val">{(i.score ?? 0).toFixed(2)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function CitationBars({
  items,
  label = "Citations (papers)",
}: {
  items: ResearchItem[];
  label?: string;
}) {
  const cited = items
    .filter((i) => i.citation_count != null && i.citation_count > 0)
    .sort((a, b) => (b.citation_count ?? 0) - (a.citation_count ?? 0))
    .slice(0, 6);
  if (cited.length === 0) return null;
  const max = Math.max(...cited.map((i) => i.citation_count ?? 1), 1);
  return (
    <div className="viz-block">
      <p className="viz-label">{label}</p>
      <div className="score-bars">
        {cited.map((i) => (
          <div key={i.url} className="score-bar-row" title={i.title}>
            <span className="score-bar-name">{i.title}</span>
            <div className="score-bar-track">
              <div
                className="score-bar-fill"
                style={{
                  width: `${Math.round(((i.citation_count ?? 0) / max) * 100)}%`,
                }}
              />
            </div>
            <span className="score-bar-val">{i.citation_count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function NewsTimeline({ items }: { items: ResearchItem[] }) {
  const dated = items.filter((i) => i.published).slice(0, 8);
  if (dated.length === 0) return null;
  return (
    <div className="viz-block">
      <p className="viz-label">News timeline</p>
      <div className="news-timeline">
        {dated.map((i) => (
          <a
            key={i.url}
            href={i.url}
            target="_blank"
            rel="noreferrer"
            className="timeline-card"
          >
            <div className="timeline-thumb">
              {i.image_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={i.image_url} alt="" loading="lazy" />
              ) : i.favicon_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={i.favicon_url} alt="" className="timeline-favicon" />
              ) : (
                <span className="timeline-placeholder" />
              )}
            </div>
            <div>
              <p className="timeline-date">{i.published}</p>
              <p className="timeline-title">{i.title}</p>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

function FindingThumb({
  imageUrl,
  faviconUrl,
  fallback,
}: {
  imageUrl?: string | null;
  faviconUrl?: string | null;
  fallback: string;
}) {
  const [failed, setFailed] = useState(false);
  const src = !failed && imageUrl ? imageUrl : null;

  if (src) {
    return (
      <div className="finding-thumb">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={src}
          alt=""
          loading="lazy"
          referrerPolicy="no-referrer"
          onError={() => setFailed(true)}
        />
      </div>
    );
  }

  return (
    <div className="finding-thumb">
      <div className="finding-thumb-empty">
        {faviconUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={faviconUrl} alt="" referrerPolicy="no-referrer" />
        ) : (
          <span>{fallback}</span>
        )}
      </div>
    </div>
  );
}

function Finding({
  item,
  index,
  layout,
}: {
  item: ResearchItem;
  index: number;
  layout: LayoutMode;
}) {
  const [open, setOpen] = useState(false);
  const meta = SOURCE_META[item.source] ?? SOURCE_META.tavily;

  return (
    <article
      className={`finding-card finding-${layout} rise${open ? " is-open" : ""}`}
      style={{ animationDelay: `${Math.min(index, 8) * 0.03}s` }}
    >
      <button
        type="button"
        className="finding-card-btn"
        onClick={() => setOpen((v) => !v)}
      >
        <FindingThumb
          imageUrl={item.image_url}
          faviconUrl={item.favicon_url}
          fallback={meta.label.slice(0, 1)}
        />
        <div className="finding-body">
          <div className="finding-meta">
            <span>
              {item.favicon_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={item.favicon_url} alt="" className="inline-favicon" referrerPolicy="no-referrer" />
              ) : null}
              {String(index + 1).padStart(2, "0")} · {meta.label} · {hostnameOf(item.url)}
            </span>
            <span>{open ? "Hide" : "Read"}</span>
          </div>
          <h3>{item.title}</h3>
          {layout === "cards" && item.content ? (
            <p className="finding-snippet">{item.content}</p>
          ) : null}
        </div>
      </button>

      {open && (
        <div className="fade-in finding-expand">
          {layout === "list" && item.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={item.image_url}
              alt=""
              className="finding-hero"
              referrerPolicy="no-referrer"
            />
          ) : null}
          <p className="finding-submeta">
            {item.published ? `${item.published} · ` : ""}
            {item.citation_count != null ? `${item.citation_count} citations · ` : ""}
            {item.score != null ? `relevance ${item.score.toFixed(2)} · ` : ""}
            {item.authors?.length ? item.authors.join(" · ") : ""}
            {item.venue ? ` — ${item.venue}` : ""}
          </p>
          {item.content ? <p className="finding-content">{item.content}</p> : null}
          <a href={item.url} target="_blank" rel="noreferrer" className="finding-open">
            Open source
          </a>
        </div>
      )}
    </article>
  );
}

function LayoutToggle({
  layout,
  onChange,
}: {
  layout: LayoutMode;
  onChange: (mode: LayoutMode) => void;
}) {
  return (
    <div className="layout-toggle" role="group" aria-label="Research view format">
      <button
        type="button"
        className={`layout-btn${layout === "cards" ? " is-active" : ""}`}
        onClick={() => onChange("cards")}
        aria-pressed={layout === "cards"}
        title="Cards"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden>
          <rect x="1" y="1" width="5" height="5" fill="currentColor" />
          <rect x="8" y="1" width="5" height="5" fill="currentColor" />
          <rect x="1" y="8" width="5" height="5" fill="currentColor" />
          <rect x="8" y="8" width="5" height="5" fill="currentColor" />
        </svg>
        <span>Cards</span>
      </button>
      <button
        type="button"
        className={`layout-btn${layout === "list" ? " is-active" : ""}`}
        onClick={() => onChange("list")}
        aria-pressed={layout === "list"}
        title="List"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden>
          <rect x="1" y="2" width="12" height="2" fill="currentColor" />
          <rect x="1" y="6" width="12" height="2" fill="currentColor" />
          <rect x="1" y="10" width="12" height="2" fill="currentColor" />
        </svg>
        <span>List</span>
      </button>
    </div>
  );
}

function ResearchLoader({ topic, stageIndex }: { topic: string; stageIndex: number }) {
  const progress = Math.min(92, ((stageIndex + 1) / LOAD_STAGES.length) * 100);

  return (
    <section
      className="sheet-up"
      style={{
        minHeight: "70vh",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        textAlign: "center",
        padding: "2rem 1rem",
      }}
    >
      <div className="loader-ring" style={{ marginBottom: "1.75rem" }} />
      <p
        style={{
          margin: 0,
          fontFamily: "var(--font-display)",
          fontSize: "clamp(2rem, 5vw, 2.75rem)",
          fontWeight: 500,
          letterSpacing: "-0.02em",
        }}
      >
        Researching
      </p>
      <p
        style={{
          margin: "0.85rem 0 1.75rem",
          maxWidth: "26rem",
          color: "var(--ink-soft)",
          lineHeight: 1.6,
        }}
      >
        “{topic}” — web, news, and papers are gathering now.
      </p>

      <div
        style={{
          width: "min(100%, 24rem)",
          height: 2,
          background: "var(--line)",
          marginBottom: "2rem",
          overflow: "hidden",
        }}
        aria-hidden
      >
        <div
          className="loader-bar"
          style={{
            width: `${progress}%`,
            height: "100%",
            background: "var(--ink)",
            transition: "width 0.6s cubic-bezier(0.22, 1, 0.36, 1)",
          }}
        />
      </div>

      <ol
        style={{
          listStyle: "none",
          margin: 0,
          padding: 0,
          width: "min(100%, 24rem)",
          textAlign: "left",
        }}
      >
        {LOAD_STAGES.map((stage, i) => {
          const done = i < stageIndex;
          const active = i === stageIndex;
          return (
            <li
              key={stage.label}
              className={active ? "stage-active" : undefined}
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: "1rem",
                padding: "0.95rem 0",
                borderTop: i === 0 ? "1px solid var(--line)" : undefined,
                borderBottom: "1px solid var(--line)",
                opacity: done || active ? 1 : 0.35,
              }}
            >
              <span>
                <span style={{ color: "var(--muted)", marginRight: "0.55rem" }}>
                  {done ? "✓" : String(i + 1).padStart(2, "0")}
                </span>
                {stage.label}
              </span>
              <span
                style={{
                  fontSize: "0.66rem",
                  letterSpacing: "0.12em",
                  textTransform: "uppercase",
                  color: "var(--muted)",
                }}
              >
                {done ? "Done" : active ? stage.tool : "Waiting"}
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

export default function Home() {
  const [view, setView] = useState<View>("hero");
  const [topic, setTopic] = useState("");
  const [limit, setLimit] = useState(6);
  const [category, setCategory] = useState<ResearchCategory>("general");
  const [loadStage, setLoadStage] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MultiSourceResearchResult | null>(null);
  const [tab, setTab] = useState<TabKey>("overview");
  const [useLlm, setUseLlm] = useState(false);
  const [reportBusy, setReportBusy] = useState(false);
  const [downloadBusy, setDownloadBusy] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [layout, setLayout] = useState<LayoutMode>("cards");
  const [cursorOn, setCursorOn] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const cursorRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const fine = window.matchMedia("(pointer: fine)").matches;
    if (reduce || !fine) return;

    let raf = 0;
    let pending = false;
    let mx = window.innerWidth * 0.5;
    let my = window.innerHeight * 0.3;
    const root = document.documentElement;

    const paint = () => {
      pending = false;
      const w = Math.max(window.innerWidth, 1);
      const h = Math.max(window.innerHeight, 1);
      const nx = mx / w - 0.5;
      const ny = my / h - 0.5;
      root.style.setProperty("--tilt-x", `${(-ny * 3.5).toFixed(2)}deg`);
      root.style.setProperty("--tilt-y", `${(nx * 4.5).toFixed(2)}deg`);
      const cur = cursorRef.current;
      if (cur) {
        cur.style.transform = `translate3d(${mx}px, ${my}px, 0)`;
      }
    };

    const onMove = (e: PointerEvent) => {
      mx = e.clientX;
      my = e.clientY;
      if (!pending) {
        pending = true;
        raf = requestAnimationFrame(paint);
      }
    };

    const onEnter = () => setCursorOn(true);
    const onLeave = () => setCursorOn(false);

    paint();
    window.addEventListener("pointermove", onMove, { passive: true });
    document.documentElement.addEventListener("mouseenter", onEnter);
    document.documentElement.addEventListener("mouseleave", onLeave);
    window.addEventListener("pointerdown", onEnter, { passive: true });
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("pointermove", onMove);
      document.documentElement.removeEventListener("mouseenter", onEnter);
      document.documentElement.removeEventListener("mouseleave", onLeave);
      window.removeEventListener("pointerdown", onEnter);
      root.classList.remove("has-custom-cursor");
    };
  }, []);

  useEffect(() => {
    const fine = window.matchMedia("(pointer: fine)").matches;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!fine || reduce) return;
    // Show cursor as soon as pointer moves once
    const arm = () => setCursorOn(true);
    window.addEventListener("pointermove", arm, { once: true, passive: true });
    return () => window.removeEventListener("pointermove", arm);
  }, []);

  useEffect(() => {
    const fine = window.matchMedia("(pointer: fine)").matches;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!fine || reduce) return;
    document.documentElement.classList.toggle("has-custom-cursor", cursorOn);
    return () => document.documentElement.classList.remove("has-custom-cursor");
  }, [cursorOn]);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "auto" });
  }, [view]);

  useEffect(() => {
    if (view === "studio") {
      const t = window.setTimeout(() => inputRef.current?.focus(), 120);
      return () => clearTimeout(t);
    }
  }, [view]);

  useEffect(() => {
    if (view !== "loading") return;
    setLoadStage(0);
    const timers = [
      window.setTimeout(() => setLoadStage(1), 700),
      window.setTimeout(() => setLoadStage(2), 1400),
      window.setTimeout(() => setLoadStage(3), 2100),
      window.setTimeout(() => setLoadStage(4), 3000),
    ];
    return () => timers.forEach(clearTimeout);
  }, [view]);

  const resultTabOrder = useMemo(() => {
    const used = new Set(
      (result?.sources_used?.length
        ? result.sources_used
        : (["tavily", "news", "papers"] as SourceKey[])
      ).filter(Boolean),
    );
    if ((result?.github_results?.length ?? 0) > 0) used.add("github");
    if (result && result.tavily_results.length > 0) used.add("tavily");
    if (result && result.news_results.length > 0) used.add("news");
    if (result && result.papers_results.length > 0) used.add("papers");
    return SOURCE_TAB_ORDER.filter(
      (k) => k === "overview" || used.has(k as SourceKey),
    );
  }, [result]);

  useEffect(() => {
    if (view !== "results" || !result) return;
    const onKey = (e: KeyboardEvent) => {
      if (tab === "report") return;
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      const order = resultTabOrder;
      const i = order.indexOf(tab);
      if (i < 0) return;
      e.preventDefault();
      const next =
        e.key === "ArrowRight"
          ? order[(i + 1) % order.length]
          : order[(i - 1 + order.length) % order.length];
      setTab(next);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [view, result, tab, resultTabOrder]);

  const runResearch = async (forceRefresh = false) => {
    if (!topic.trim()) return;
    setView("loading");
    setError(null);
    setResult(null);
    setTab("overview");
    setExportError(null);
    try {
      const res = await fetch(`${API_BASE}/api/research/multi`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic: topic.trim(),
          limit,
          category,
          force_refresh: forceRefresh,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        const detail = data.detail;
        throw new Error(
          typeof detail === "string"
            ? detail
            : typeof detail === "object"
              ? JSON.stringify(detail)
              : `Request failed (${res.status})`,
        );
      }
      setResult(data as MultiSourceResearchResult);
      setView("results");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
      setView("studio");
    }
  };

  const generateReport = async (forceRefresh = false) => {
    if (!result) return;
    setReportBusy(true);
    setExportError(null);
    setTab("report");
    try {
      const res = await fetch(`${API_BASE}/api/research/synthesize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic: result.topic,
          tavily_results: result.tavily_results,
          news_results: result.news_results,
          papers_results: result.papers_results,
          github_results: result.github_results || [],
          tavily_answer: result.tavily_answer,
          media_urls: result.media_urls || [],
          use_llm: useLlm,
          force_refresh: forceRefresh,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        const detail = data.detail;
        throw new Error(
          typeof detail === "string"
            ? detail
            : typeof detail === "object"
              ? JSON.stringify(detail)
              : `Request failed (${res.status})`,
        );
      }
      const next = data as MultiSourceResearchResult;
      setResult({
        ...result,
        report: next.report,
        report_error: next.report_error,
        media_urls: next.media_urls?.length ? next.media_urls : result.media_urls,
        cached: next.cached,
        cache_key: next.cache_key,
      });
    } catch (e) {
      setExportError(e instanceof Error ? e.message : "Report failed");
    } finally {
      setReportBusy(false);
    }
  };

  const handleDownload = async (kind: "md" | "json" | "pdf") => {
    if (!result?.report) return;
    setDownloadBusy(true);
    setExportError(null);
    try {
      const payload = result.report as unknown as Record<string, unknown>;
      if (kind === "md") await downloadReportMarkdown(payload, result.topic);
      else if (kind === "json") await downloadReportJson(payload, result.topic);
      else await openReportPrintPdf(payload);
    } catch (e) {
      setExportError(e instanceof Error ? e.message : "Download failed");
    } finally {
      setDownloadBusy(false);
    }
  };

  const totals = useMemo(() => {
    if (!result) return null;
    const github = result.github_results?.length ?? 0;
    return {
      web: result.tavily_results.length,
      news: result.news_results.length,
      papers: result.papers_results.length,
      github,
      all:
        result.tavily_results.length +
        result.news_results.length +
        result.papers_results.length +
        github,
    };
  }, [result]);

  const activeCategory = useMemo(
    () => CATEGORIES.find((c) => c.id === category) ?? CATEGORIES[0],
    [category],
  );

  const activeItems: ResearchItem[] = useMemo(() => {
    if (!result) return [];
    if (tab === "tavily") return result.tavily_results;
    if (tab === "news") return result.news_results;
    if (tab === "papers") return result.papers_results;
    if (tab === "github") return result.github_results || [];
    return [];
  }, [result, tab]);

  const overviewItems: ResearchItem[] = useMemo(() => {
    if (!result) return [];
    return [
      ...result.tavily_results,
      ...result.news_results,
      ...result.papers_results,
      ...(result.github_results || []),
    ];
  }, [result]);

  return (
    <div style={{ minHeight: "100vh", position: "relative" }}>
      <div className="bg-grain" aria-hidden />
      <div
        ref={cursorRef}
        className={`app-cursor${cursorOn ? " is-on" : ""}`}
        aria-hidden
      >
        <span className="app-cursor-ring" />
        <span className="app-cursor-dot" />
      </div>
      {/* Persistent navbar */}
      <header className="site-header">
        <div className="site-header-inner">
          <button
            type="button"
            className="site-brand"
            onClick={() => {
              setView("hero");
              setError(null);
            }}
          >
            Atelier
          </button>

          <nav className="site-nav" aria-label="Primary">
            <button
              type="button"
              className={`site-nav-link${view === "hero" ? " is-active" : ""}`}
              onClick={() => {
                setView("hero");
                setError(null);
              }}
            >
              Home
            </button>
            <button
              type="button"
              className="site-nav-link"
              onClick={() => {
                setView("hero");
                window.setTimeout(() => {
                  document.getElementById("how-it-works")?.scrollIntoView({
                    behavior: "smooth",
                  });
                }, 40);
              }}
            >
              How it works
            </button>
            <button
              type="button"
              className="site-nav-link"
              onClick={() => {
                setView("hero");
                window.setTimeout(() => {
                  document.getElementById("capabilities")?.scrollIntoView({
                    behavior: "smooth",
                  });
                }, 40);
              }}
            >
              Sources
            </button>
            <button
              type="button"
              className="site-nav-link"
              onClick={() => {
                setView("hero");
                window.setTimeout(() => {
                  document.getElementById("report")?.scrollIntoView({
                    behavior: "smooth",
                  });
                }, 40);
              }}
            >
              Report
            </button>
            <button
              type="button"
              className={`site-nav-link${view === "studio" ? " is-active" : ""}`}
              onClick={() => setView("studio")}
            >
              Studio
            </button>
            {view === "results" && (
              <button
                type="button"
                className="site-nav-link is-active"
                onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
              >
                Results
              </button>
            )}
          </nav>

          <div className="site-header-actions">
            {view !== "hero" && view !== "loading" && view !== "studio" && (
              <button
                type="button"
                className="btn-3d-ghost site-header-btn"
                onClick={() => setView("studio")}
              >
                New topic
              </button>
            )}
            <button
              type="button"
              className="btn-3d site-header-btn"
              onClick={() => setView("studio")}
            >
              Research
            </button>
          </div>
        </div>
      </header>

      {view === "hero" && <HeroHome onResearch={() => setView("studio")} />}

      {/* STUDIO — open research sheet */}
      {view === "studio" && (
        <main className="sheet-up studio-shell">
          <p
            style={{
              margin: 0,
              fontSize: "0.7rem",
              letterSpacing: "0.18em",
              textTransform: "uppercase",
              color: "var(--muted)",
            }}
          >
            Research studio
          </p>
          <h1
            style={{
              margin: "0.75rem 0 0",
              fontFamily: "var(--font-display)",
              fontSize: "clamp(2.2rem, 5vw, 3.2rem)",
              fontWeight: 500,
              letterSpacing: "-0.03em",
              lineHeight: 1.05,
            }}
          >
            What should we look into?
          </h1>
          <p style={{ margin: "1rem 0 0", color: "var(--ink-soft)", lineHeight: 1.6, maxWidth: "30rem" }}>
            Pick a research type — we’ll pull the right mix of web, news, papers, and GitHub. Generate a report when you’re ready.
          </p>

          <div style={{ marginTop: "2rem" }}>
            <p
              style={{
                margin: "0 0 0.65rem",
                fontSize: "0.66rem",
                letterSpacing: "0.14em",
                textTransform: "uppercase",
                color: "var(--muted)",
              }}
            >
              Research type
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
              {CATEGORIES.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  className={`chip${category === c.id ? " is-active" : ""}`}
                  onClick={() => setCategory(c.id)}
                  title={c.blurb}
                >
                  {c.label}
                </button>
              ))}
            </div>
            <p style={{ margin: "0.75rem 0 0", fontSize: "0.85rem", color: "var(--ink-soft)" }}>
              {activeCategory.blurb}
            </p>
          </div>

          <label
            htmlFor="topic"
            style={{
              display: "block",
              marginTop: "2rem",
              fontSize: "0.68rem",
              letterSpacing: "0.16em",
              textTransform: "uppercase",
              color: "var(--muted)",
            }}
          >
            Topic
          </label>
          <input
            ref={inputRef}
            id="topic"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && void runResearch()}
            placeholder="AI for founders automate tasks"
            style={{
              width: "100%",
              marginTop: "0.65rem",
              border: "none",
              borderBottom: "1px solid var(--ink)",
              background: "transparent",
              padding: "0.85rem 0",
              fontFamily: "var(--font-display)",
              fontSize: "clamp(1.35rem, 3vw, 1.85rem)",
              fontWeight: 500,
              outline: "none",
              color: "var(--ink)",
            }}
          />

          <div style={{ marginTop: "1.35rem" }}>
            <p
              style={{
                margin: "0 0 0.65rem",
                fontSize: "0.66rem",
                letterSpacing: "0.14em",
                textTransform: "uppercase",
                color: "var(--muted)",
              }}
            >
              Try an example
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
              {activeCategory.examples.map((ex) => (
                <button
                  key={ex}
                  type="button"
                  className="chip"
                  onClick={() => {
                    setTopic(ex);
                    inputRef.current?.focus();
                  }}
                >
                  {ex}
                </button>
              ))}
            </div>
          </div>

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: "1rem",
              marginTop: "2rem",
              flexWrap: "wrap",
            }}
          >
            <label style={{ fontSize: "0.82rem", color: "var(--muted)", display: "inline-flex", gap: "0.5rem", alignItems: "center" }}>
              Depth
              <input
                type="number"
                min={1}
                max={20}
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value) || 6)}
                style={{
                  width: 56,
                  border: "1px solid var(--line)",
                  background: "var(--surface)",
                  padding: "0.4rem",
                  borderRadius: 0,
                }}
              />
              <span style={{ fontSize: "0.72rem" }}>per source</span>
            </label>
            <div style={{ display: "flex", gap: "0.75rem" }}>
              <button type="button" className="btn-3d-ghost" onClick={() => setView("hero")}>
                Back
              </button>
              <button
                type="button"
                className="btn-3d"
                disabled={!topic.trim()}
                onClick={() => runResearch()}
              >
                Start research
              </button>
            </div>
          </div>

          {error && (
            <p
              style={{
                marginTop: "1.5rem",
                color: "var(--warn)",
                borderLeft: "2px solid var(--warn)",
                paddingLeft: "0.85rem",
              }}
            >
              {error}
            </p>
          )}

          <div
            style={{
              display: "grid",
              gridTemplateColumns: `repeat(${Math.min(activeCategory.sources.length, 4)}, 1fr)`,
              gap: "0.75rem",
              marginTop: "3rem",
              borderTop: "1px solid var(--line)",
              paddingTop: "1.5rem",
            }}
          >
            {activeCategory.sources.map((key) => (
              <div key={key}>
                <p style={{ margin: 0, fontFamily: "var(--font-display)", fontSize: "1.2rem" }}>
                  {SOURCE_META[key].label}
                </p>
                <p style={{ margin: "0.3rem 0 0", fontSize: "0.72rem", color: "var(--muted)", letterSpacing: "0.06em" }}>
                  {SOURCE_META[key].tool}
                </p>
              </div>
            ))}
          </div>
        </main>
      )}

      {view === "loading" && (
        <ResearchLoader topic={topic.trim()} stageIndex={loadStage} />
      )}

      {/* RESULTS */}
      {view === "results" && result && totals && (
        <main
          className="sheet-up"
          style={{
            maxWidth: 920,
            margin: "0 auto",
            padding: "0.5rem clamp(1.25rem, 4vw, 2rem) 4.5rem",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "end",
              gap: "1rem",
              marginBottom: "1.25rem",
              flexWrap: "wrap",
            }}
          >
            <div>
              <p
                style={{
                  margin: 0,
                  fontSize: "0.68rem",
                  letterSpacing: "0.16em",
                  textTransform: "uppercase",
                  color: "var(--muted)",
                }}
              >
                Research · {totals.all} sources
                {result.cached ? " · cached" : ""}
              </p>
              <h2
                style={{
                  margin: "0.4rem 0 0",
                  fontFamily: "var(--font-display)",
                  fontSize: "clamp(1.7rem, 3.5vw, 2.3rem)",
                  fontWeight: 500,
                  letterSpacing: "-0.02em",
                  maxWidth: "28rem",
                  lineHeight: 1.15,
                }}
              >
                {result.topic}
              </h2>
            </div>
            <div style={{ display: "flex", gap: "0.55rem", flexWrap: "wrap" }}>
              <button
                type="button"
                className="btn-3d-ghost"
                style={{ padding: "0.7rem 1rem" }}
                onClick={() => setView("studio")}
              >
                New research
              </button>
              <button
                type="button"
                className="btn-3d-ghost"
                style={{ padding: "0.7rem 1rem" }}
                title="Bypass cache and fetch fresh sources"
                onClick={() => {
                  setTopic(result.topic);
                  void runResearch(true);
                }}
              >
                Refresh
              </button>
            </div>
          </div>

          <div className={`report-cta${tab === "report" ? " is-active" : ""}`}>
            <div className="report-cta-copy">
              <p className="report-cta-kicker">
                {result.report ? "Report ready" : "Next step"}
              </p>
              <p className="report-cta-title">
                {result.report
                  ? "Open your research report"
                  : "Get the full research report"}
              </p>
              <p className="report-cta-body">
                {result.report
                  ? "Summary, ranked findings, news, papers, gaps, and downloads — Markdown, JSON, or PDF."
                  : "Turn these sources into a readable report with findings and export options."}
              </p>
            </div>
            <button
              type="button"
              className="btn-3d report-cta-btn"
              onClick={() => setTab("report")}
            >
              {tab === "report"
                ? "Viewing report"
                : result.report
                  ? "Open report"
                  : "Generate report"}
            </button>
          </div>

          {tab !== "report" && (
          <nav className="cat-rail" aria-label="Categories">
            {(
              [
                ["overview", "Overview", totals.all],
                ["tavily", "Web", totals.web],
                ["news", "News", totals.news],
                ["papers", "Papers", totals.papers],
                ["github", "GitHub", totals.github],
              ] as const
            )
              .filter(([key]) => resultTabOrder.includes(key))
              .map(([key, label, count]) => {
              const pct =
                totals.all > 0 ? Math.max(8, Math.round((count / totals.all) * 100)) : 0;
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => setTab(key)}
                  className={`cat-btn${tab === key ? " is-active" : ""}`}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", gap: "0.5rem" }}>
                    <span
                      style={{
                        fontSize: "0.72rem",
                        letterSpacing: "0.1em",
                        textTransform: "uppercase",
                        fontWeight: 500,
                      }}
                    >
                      {label}
                    </span>
                    <span className="count">{count}</span>
                  </div>
                  <div className="cat-meter" aria-hidden>
                    <span style={{ width: `${pct}%` }} />
                  </div>
                </button>
              );
            })}
          </nav>
          )}
          {tab !== "report" && (
          <p
            style={{
              margin: "-0.75rem 0 1.25rem",
              fontSize: "0.72rem",
              color: "var(--muted)",
            }}
          >
            Browse sources · ← → keys
          </p>
          )}

          {tab === "report" && (
            <div key="report" style={{ marginTop: "0.5rem" }}>
              <div style={{ marginBottom: "1.25rem" }}>
                <button
                  type="button"
                  className="btn-3d-ghost"
                  style={{ padding: "0.55rem 0.9rem" }}
                  onClick={() => setTab("overview")}
                >
                  ← Back to sources
                </button>
              </div>              {!result.report && !reportBusy && (
                <div
                  className="rise"
                  style={{
                    border: "1px solid var(--ink)",
                    padding: "1.75rem 1.35rem",
                    background: "var(--surface)",
                    boxShadow: "0 4px 0 #2a2a2a",
                    marginBottom: "1.5rem",
                  }}
                >
                  <p
                    style={{
                      margin: 0,
                      fontFamily: "var(--font-display)",
                      fontSize: "1.6rem",
                      fontWeight: 500,
                    }}
                  >
                    Build your report
                  </p>
                  <p style={{ margin: "0.65rem 0 0", color: "var(--ink-soft)", lineHeight: 1.6, maxWidth: "36rem" }}>
                    Compile a report from the sources you already gathered — summary,
                    ranked findings, news, papers, gaps, and downloads. Optional AI rewrite
                    uses Gemini.
                  </p>
                  <label
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "0.55rem",
                      marginTop: "1.25rem",
                      fontSize: "0.85rem",
                      color: "var(--ink-soft)",
                      cursor: "pointer",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={useLlm}
                      onChange={(e) => setUseLlm(e.target.checked)}
                    />
                    Enhance with AI (Gemini)
                  </label>
                  <div style={{ marginTop: "1.35rem", display: "flex", gap: "0.65rem", flexWrap: "wrap" }}>
                    <button type="button" className="btn-3d" onClick={() => generateReport(false)}>
                      Generate report
                    </button>
                    {result.report && (
                      <button
                        type="button"
                        className="btn-3d-ghost"
                        onClick={() => generateReport(true)}
                      >
                        Regenerate
                      </button>
                    )}
                  </div>
                  {exportError && (
                    <p style={{ marginTop: "1rem", color: "var(--warn)" }}>{exportError}</p>
                  )}
                </div>
              )}

              {reportBusy && (
                <div style={{ padding: "2.5rem 0", textAlign: "center" }}>
                  <div className="loader-ring" style={{ margin: "0 auto 1rem" }} />
                  <p style={{ fontFamily: "var(--font-display)", fontSize: "1.5rem", margin: 0 }}>
                    {useLlm ? "Writing report with Gemini…" : "Compiling report…"}
                  </p>
                </div>
              )}

              {result.report && !reportBusy && (
                <ResearchReportView
                  report={result.report}
                  reportError={result.report_error}
                  onDownloadMd={() => handleDownload("md")}
                  onDownloadJson={() => handleDownload("json")}
                  onDownloadPdf={() => handleDownload("pdf")}
                  downloading={downloadBusy}
                />
              )}
              {exportError && result.report && (
                <p style={{ marginTop: "1rem", color: "var(--warn)" }}>{exportError}</p>
              )}
            </div>
          )}

          {tab === "overview" && (
            <div className="rise" key="overview">
              {result.tavily_answer && (
                <aside
                  style={{
                    marginBottom: "1.75rem",
                    padding: "1.35rem 1.2rem",
                    border: "1px solid var(--ink)",
                    background: "var(--surface)",
                    boxShadow: "0 4px 0 #2a2a2a",
                  }}
                >
                  <p
                    style={{
                      margin: 0,
                      fontSize: "0.66rem",
                      letterSpacing: "0.16em",
                      textTransform: "uppercase",
                      color: "var(--muted)",
                    }}
                  >
                    Synthesis · Tavily
                  </p>
                  <p
                    style={{
                      margin: "0.85rem 0 0",
                      fontFamily: "var(--font-display)",
                      fontSize: "clamp(1.15rem, 2.2vw, 1.4rem)",
                      lineHeight: 1.45,
                      fontWeight: 500,
                    }}
                  >
                    {result.tavily_answer}
                  </p>
                </aside>
              )}

              <NewsTimeline items={result.news_results} />
              <div className="viz-grid">
                <SourceMixChart
                  stats={{
                    web: totals.web,
                    news: totals.news,
                    papers: totals.papers,
                    github: totals.github,
                    total: totals.all,
                  }}
                />
                <ScoreBars items={result.tavily_results} />
                <CitationBars items={result.papers_results} />
                <CitationBars
                  items={result.github_results || []}
                  label="Stars (GitHub)"
                />
              </div>

              <p style={{ margin: "1.5rem 0 1.15rem", color: "var(--ink-soft)", lineHeight: 1.6 }}>
                Jump into a stack — cards use real previews from the pages (not AI images).
              </p>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "0.9rem",
                }}
              >
                {(
                  [
                    ["tavily", totals.web, result.tavily_results],
                    ["news", totals.news, result.news_results],
                    ["papers", totals.papers, result.papers_results],
                    ["github", totals.github, result.github_results || []],
                  ] as const
                )
                  .filter(([key]) => resultTabOrder.includes(key))
                  .map(([key, count, items]) => {
                  const m = SOURCE_META[key];
                  const cover = items.find((it) => it.image_url)?.image_url;
                  return (
                    <button
                      key={key}
                      type="button"
                      className="source-card source-card-visual"
                      onClick={() => setTab(key)}
                    >
                      <div className="source-card-cover">
                        {cover ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={cover} alt="" />
                        ) : (
                          <span>{m.label}</span>
                        )}
                      </div>
                      <p
                        style={{
                          margin: "0.85rem 0 0",
                          fontSize: "0.66rem",
                          letterSpacing: "0.14em",
                          textTransform: "uppercase",
                          color: "var(--muted)",
                        }}
                      >
                        {m.tool}
                      </p>
                      <p
                        style={{
                          margin: "0.35rem 0 0",
                          fontFamily: "var(--font-display)",
                          fontSize: "1.65rem",
                          fontWeight: 500,
                        }}
                      >
                        {m.label}
                      </p>
                      <p style={{ margin: "0.35rem 0 0", fontSize: "0.85rem", color: "var(--ink-soft)" }}>
                        {count} finding{count === 1 ? "" : "s"}
                      </p>
                      <ul className="preview">
                        {items.slice(0, 2).map((it, i) => (
                          <li key={`${it.url}-p-${i}`}>{it.title}</li>
                        ))}
                        {items.length === 0 && <li>No items yet</li>}
                      </ul>
                    </button>
                  );
                })}
              </div>

              <header
                style={{
                  marginTop: "2.25rem",
                  marginBottom: "1rem",
                  display: "flex",
                  justifyContent: "space-between",
                  gap: "1rem",
                  alignItems: "end",
                  flexWrap: "wrap",
                }}
              >
                <div>
                  <p
                    style={{
                      margin: 0,
                      fontSize: "0.66rem",
                      letterSpacing: "0.16em",
                      textTransform: "uppercase",
                      color: "var(--muted)",
                    }}
                  >
                    All sources · {overviewItems.length} findings
                  </p>
                  <h3
                    style={{
                      margin: "0.35rem 0 0",
                      fontFamily: "var(--font-display)",
                      fontSize: "2.1rem",
                      fontWeight: 500,
                    }}
                  >
                    Findings
                  </h3>
                </div>
                <LayoutToggle layout={layout} onChange={setLayout} />
              </header>
              <div
                className="rule-grow"
                style={{ height: 1, background: "var(--ink)", margin: "0 0 1rem" }}
              />
              <div className={layout === "cards" ? "findings-grid" : "findings-list panel-scroll"}>
                {overviewItems.length === 0 ? (
                  <p style={{ color: "var(--muted)" }}>No findings yet.</p>
                ) : (
                  overviewItems.map((item, i) => (
                    <Finding
                      key={`overview-${item.url}-${i}`}
                      item={item}
                      index={i}
                      layout={layout}
                    />
                  ))
                )}
              </div>
            </div>
          )}

          {tab !== "overview" && tab !== "report" && (
            <div className="rise" key={tab}>
              <header
                style={{
                  marginBottom: "1rem",
                  display: "flex",
                  justifyContent: "space-between",
                  gap: "1rem",
                  alignItems: "end",
                  flexWrap: "wrap",
                }}
              >
                <div>
                  <p
                    style={{
                      margin: 0,
                      fontSize: "0.66rem",
                      letterSpacing: "0.16em",
                      textTransform: "uppercase",
                      color: "var(--muted)",
                    }}
                  >
                    Scraped with {SOURCE_META[tab].tool}
                  </p>
                  <h3
                    style={{
                      margin: "0.35rem 0 0",
                      fontFamily: "var(--font-display)",
                      fontSize: "2.1rem",
                      fontWeight: 500,
                    }}
                  >
                    {SOURCE_META[tab].label}
                  </h3>
                </div>
                <div style={{ display: "flex", gap: "0.45rem", alignItems: "center" }}>
                  <LayoutToggle layout={layout} onChange={setLayout} />
                </div>
              </header>
              <div
                className="rule-grow"
                style={{ height: 1, background: "var(--ink)", margin: "0 0 0.85rem" }}
              />
              <p style={{ margin: "0 0 1rem", fontSize: "0.9rem", color: "var(--ink-soft)", lineHeight: 1.55 }}>
                {SOURCE_META[tab].method}
              </p>
              {result.errors?.[tab] && (
                <p style={{ margin: "0 0 0.7rem", color: "var(--warn)", fontSize: "0.88rem" }}>
                  {result.errors[tab]}
                </p>
              )}
              <div className={layout === "cards" ? "findings-grid" : "findings-list panel-scroll"}>
                {activeItems.length === 0 ? (
                  <p style={{ color: "var(--muted)" }}>No findings in this category.</p>
                ) : (
                  activeItems.map((item, i) => (
                    <Finding
                      key={`${item.url}-${i}`}
                      item={item}
                      index={i}
                      layout={layout}
                    />
                  ))
                )}
              </div>
            </div>
          )}
        </main>
      )}
    </div>
  );
}
