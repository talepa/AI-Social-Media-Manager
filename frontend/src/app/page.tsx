"use client";

/**
 * Prompt-first research UI with auto-routing.
 */

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import GeminiThread, {
  type ChatMessage,
  type ModeSwitchProposal,
  type ResearchProposal,
} from "../components/GeminiThread";
import ChatSidebar from "../components/ChatSidebar";
import AtelierMark from "../components/AtelierMark";
import {
  deleteChatSession,
  getChatSession,
  loadChatSessions,
  sessionTitle,
  upsertChatSession,
  type StoredChatSession,
} from "../lib/chatHistory";
import { sourceTabsForResult } from "../components/SourcePanel";
import type { DisplayTab } from "../lib/partitionResults";
import {
  getExpandPermission,
  getModeSwitchPermission,
  setExpandPermission,
  setModeSwitchPermission,
} from "../lib/researchPermission";
import { formatDomain, formatSources } from "../lib/productConfig";
import type { ResearchRoutingPlan, ResearchRunMode } from "../lib/productTypes";
import {
  downloadReportJson,
  downloadReportMarkdown,
  openReportPrintPdf,
} from "../lib/reportDownload";

const API_BASE = "http://localhost:8001";

type View = "home" | "session";
type SourceKey = "tavily" | "news" | "papers" | "github";
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
  routing?: ResearchRoutingPlan | null;
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

const LOAD_STAGES = [
  { label: "Scanning the web", tool: "Tavily" },
  { label: "Collecting headlines", tool: "Google News" },
  { label: "Reading papers", tool: "OpenAlex / S2" },
  { label: "Searching GitHub", tool: "Repos" },
  { label: "Organising findings", tool: "LangGraph" },
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

function msgId() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function clearMessageSources(messages: ChatMessage[]): ChatMessage[] {
  return messages.map((m) => ({ ...m, showSources: false }));
}

function preferSourceTab(result: MultiSourceResearchResult): DisplayTab | null {
  const tabs = sourceTabsForResult(result);
  return (
    tabs.find((t) => t === "youtube") ??
    tabs.find((t) => t === "github") ??
    tabs[0] ??
    null
  );
}

export default function Home() {
  const [view, setView] = useState<View>("home");
  const [topic, setTopic] = useState("");
  const [runMode, setRunMode] = useState<ResearchRunMode>("research");
  const [pendingRouting, setPendingRouting] = useState<ResearchRoutingPlan | null>(null);
  const [loadStage, setLoadStage] = useState(0);
  const [sessionLoading, setSessionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MultiSourceResearchResult | null>(null);
  const [sourceTab, setSourceTab] = useState<DisplayTab | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const [expanding, setExpanding] = useState(false);
  const [useLlm, setUseLlm] = useState(false);
  const [reportBusy, setReportBusy] = useState(false);
  const [downloadBusy, setDownloadBusy] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [cursorOn, setCursorOn] = useState(false);
  const [sessions, setSessions] = useState<StoredChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const cursorRef = useRef<HTMLDivElement | null>(null);
  const sessionCreatedAtRef = useRef<number>(Date.now());

  useEffect(() => {
    setSessions(loadChatSessions());
  }, []);

  const refreshSessions = () => setSessions(loadChatSessions());

  const saveActiveSession = (
    override?: Partial<{
      messages: ChatMessage[];
      result: MultiSourceResearchResult | null;
      topic: string;
      runMode: ResearchRunMode;
      sourceTab: DisplayTab | null;
    }>,
  ) => {
    if (!activeSessionId) return;
    const m = override?.messages ?? messages;
    if (m.length === 0) return;
    const t = override?.topic ?? topic;
    const r = override?.result ?? result;
    const rm = override?.runMode ?? runMode;
    const tab = override?.sourceTab ?? sourceTab;
    upsertChatSession({
      id: activeSessionId,
      title: sessionTitle(m, t),
      topic: t,
      runMode: rm,
      messages: m,
      result: r,
      sourceTab: tab,
      createdAt: sessionCreatedAtRef.current,
      updatedAt: Date.now(),
    });
    refreshSessions();
  };

  useEffect(() => {
    saveActiveSession();
  }, [messages, result, topic, runMode, sourceTab, activeSessionId]);

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
      root.style.setProperty("--mouse-x", (mx / w).toFixed(4));
      root.style.setProperty("--mouse-y", (my / h).toFixed(4));
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
    if (!sessionLoading) return;
    setLoadStage(0);
    const timers = [
      window.setTimeout(() => setLoadStage(1), 600),
      window.setTimeout(() => setLoadStage(2), 1200),
      window.setTimeout(() => setLoadStage(3), 1900),
      window.setTimeout(() => setLoadStage(4), 2600),
      window.setTimeout(() => setLoadStage(5), 3400),
    ];
    return () => timers.forEach(clearTimeout);
  }, [sessionLoading]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const q = params.get("q")?.trim();
    if (q && view === "home" && !topic) {
      setTopic(q);
    }
  }, [view, topic]);

  const stripUrls = (text: string) =>
    text.replace(/https?:\/\/\S+/g, "").replace(/\n{3,}/g, "\n\n").trim();

  const fetchOpeningSummary = async (
    data: MultiSourceResearchResult,
    mode: ResearchRunMode,
  ): Promise<{ content: string; plan?: import("../lib/planTypes").ResearchPlan | null }> => {
    if (mode === "plan") {
      try {
        const res = await fetch(`${API_BASE}/api/research/plan`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ research: data, use_llm: false }),
        });
        if (res.ok) {
          const payload = (await res.json()) as {
            plan?: import("../lib/planTypes").ResearchPlan;
            markdown?: string;
          };
          if (payload.plan) {
            return {
              content: payload.markdown?.trim() || payload.plan.headline,
              plan: payload.plan,
            };
          }
        }
      } catch {
        /* fall through */
      }
    }

    if (data.tavily_answer?.trim()) {
      return { content: stripUrls(data.tavily_answer.trim()).slice(0, 900) };
    }
    try {
      const res = await fetch(`${API_BASE}/api/research/summary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (res.ok) {
        const payload = (await res.json()) as { summary?: string };
        if (payload.summary?.trim()) return { content: payload.summary.trim() };
      }
    } catch {
      /* use fallback below */
    }
    return {
      content:
        mode === "plan"
          ? "Plan ready — see structured sections below."
          : "Research complete — browse the sources below or ask a follow-up.",
    };
  };

  const runResearch = async (forceRefresh = false) => {
    if (!topic.trim()) return;
    const q = topic.trim();
    const sessionId = msgId();
    sessionCreatedAtRef.current = Date.now();
    setActiveSessionId(sessionId);
    setView("session");
    setSessionLoading(true);
    setError(null);
    setResult(null);
    setExportError(null);
    setPendingRouting(null);
    setMessages([{ id: msgId(), role: "user", content: q }]);
    setChatInput("");
    setSourceTab(null);
    try {
      const routeRes = await fetch(`${API_BASE}/api/research/route`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: q, run_mode: runMode }),
      });
      if (routeRes.ok) {
        setPendingRouting((await routeRes.json()) as ResearchRoutingPlan);
      }

      const res = await fetch(`${API_BASE}/api/research/multi`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic: q,
          run_mode: runMode,
          auto_route: true,
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
      setResult(next);
      if (next.routing) setPendingRouting(next.routing);
      const opening = await fetchOpeningSummary(next, runMode);
      setMessages((prev) => [
        ...clearMessageSources(prev),
        {
          id: msgId(),
          role: "assistant",
          content: opening.content,
          plan: opening.plan ?? undefined,
          showSources: true,
          sourcesCollapsed: runMode === "plan",
        },
      ]);
      const prefer = preferSourceTab(next);
      setSourceTab(prefer);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
      setView("home");
      setMessages([]);
    } finally {
      setSessionLoading(false);
    }
  };

  const runModeSwitch = async (
    messageId: string,
    permission: "once" | "always",
    proposalOverride?: ModeSwitchProposal,
  ) => {
    if (!result || expanding) return;
    const msg = messages.find((m) => m.id === messageId);
    const proposal = proposalOverride ?? msg?.modeProposal;
    if (!proposal) return;
    if (permission === "always") setModeSwitchPermission("always");

    const newMode = proposal.suggestedMode;
    const researchTopic = result.topic;

    setRunMode(newMode);
    setExpanding(true);
    setMessages((prev) =>
      prev.map((m) =>
        m.id === messageId
          ? { ...m, modeProposalStatus: "accepted" as const, loading: true }
          : m,
      ),
    );
    try {
      const res = await fetch(`${API_BASE}/api/research/multi`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic: researchTopic,
          run_mode: newMode,
          auto_route: true,
          force_refresh: true,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        const detail = data.detail;
        throw new Error(
          typeof detail === "string" ? detail : `Mode switch failed (${res.status})`,
        );
      }
      const next = data as MultiSourceResearchResult;
      setResult(next);
      if (next.routing) setPendingRouting(next.routing);
      const opening = await fetchOpeningSummary(next, newMode);
      setMessages((prev) =>
        prev.map((m) => {
          if (m.id === messageId) {
            return {
              ...m,
              loading: false,
              modeProposal: undefined,
              content: opening.content,
              plan: opening.plan ?? undefined,
              showSources: true,
              sourcesCollapsed: newMode === "plan",
            };
          }
          return { ...m, showSources: false };
        }),
      );
      setSourceTab(preferSourceTab(next));
    } catch (e) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === messageId
            ? {
                ...m,
                loading: false,
                modeProposalStatus: "pending" as const,
                content: e instanceof Error ? e.message : "Mode switch failed",
              }
            : m,
        ),
      );
    } finally {
      setExpanding(false);
    }
  };

  const sendFollowUp = async (overrideQuestion?: string) => {
    const question = (overrideQuestion ?? chatInput).trim();
    if (!question || !result || chatBusy || sessionLoading || expanding) return;

    const last = messages[messages.length - 1];
    if (
      last?.role === "user" &&
      last.content === question &&
      messages.some((m) => m.loading)
    ) {
      return;
    }

    if (!overrideQuestion) setChatInput("");
    const assistId = msgId();
    const userId = msgId();
    const prior = [...messages, { id: userId, role: "user" as const, content: question }];
    setMessages([
      ...prior,
      { id: assistId, role: "assistant", content: "", loading: true },
    ]);
    setChatBusy(true);
    try {
      const autoExpand = getExpandPermission() === "always";
      const autoModeSwitch = getModeSwitchPermission() === "always";
      const res = await fetch(`${API_BASE}/api/research/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          messages: prior.map(({ role, content }) => ({ role, content })),
          research: result,
          run_mode: runMode,
          auto_expand: autoExpand,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        const detail = data.detail;
        throw new Error(typeof detail === "string" ? detail : `Chat failed (${res.status})`);
      }
      const payload = data as {
        answer?: string;
        action?: string;
        proposal?: ResearchProposal;
        mode_proposal?: {
          suggested_mode: ResearchRunMode;
          reason: string;
          query?: string;
        };
        research?: MultiSourceResearchResult;
        plan?: import("../lib/planTypes").ResearchPlan;
        plan_markdown?: string;
      };

      if (
        payload.action === "propose_mode_switch" &&
        payload.mode_proposal &&
        autoModeSwitch
      ) {
        const modeProposal: ModeSwitchProposal = {
          suggestedMode: payload.mode_proposal.suggested_mode,
          reason: payload.mode_proposal.reason,
          query: payload.mode_proposal.query,
        };
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistId
              ? {
                  ...m,
                  content: payload.answer ?? "Switching mode…",
                  loading: false,
                  modeProposal,
                  modeProposalStatus: "accepted" as const,
                }
              : m,
          ),
        );
        await runModeSwitch(assistId, "always", modeProposal);
        return;
      }

      const gotNewResearch = Boolean(payload.research);
      if (payload.research) {
        setResult(payload.research);
        const prefer = preferSourceTab(payload.research);
        if (prefer) setSourceTab(prefer);
      }
      setMessages((prev) =>
        prev.map((m) => {
          if (m.id !== assistId) {
            return gotNewResearch ? { ...m, showSources: false } : m;
          }
          return {
            ...m,
            content: payload.answer ?? "No answer returned.",
            loading: false,
            plan: payload.plan ?? m.plan,
            proposal:
              payload.action === "propose_research" ? payload.proposal : undefined,
            proposalStatus:
              payload.action === "propose_research" ? ("pending" as const) : undefined,
            modeProposal:
              payload.action === "propose_mode_switch" && payload.mode_proposal
                ? {
                    suggestedMode: payload.mode_proposal.suggested_mode,
                    reason: payload.mode_proposal.reason,
                    query: payload.mode_proposal.query,
                  }
                : undefined,
            modeProposalStatus:
              payload.action === "propose_mode_switch" ? ("pending" as const) : undefined,
            showSources: gotNewResearch,
            sourcesCollapsed: runMode === "plan" || Boolean(payload.plan),
          };
        }),
      );
    } catch (e) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistId
            ? {
                ...m,
                loading: false,
                content: e instanceof Error ? e.message : "Chat failed",
              }
            : m,
        ),
      );
    } finally {
      setChatBusy(false);
    }
  };

  const runExpand = async (messageId: string, mode: "once" | "always") => {
    if (!result || expanding) return;
    const msg = messages.find((m) => m.id === messageId);
    if (!msg?.proposal) return;
    if (mode === "always") setExpandPermission("always");

    const question =
      [...messages].reverse().find((m) => m.role === "user")?.content ?? msg.proposal.query;

    setExpanding(true);
    setMessages((prev) =>
      prev.map((m) =>
        m.id === messageId
          ? { ...m, proposalStatus: "accepted" as const, loading: true }
          : m,
      ),
    );
    try {
      const res = await fetch(`${API_BASE}/api/research/expand`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          query: msg.proposal.query,
          sources: msg.proposal.sources,
          research: result,
          messages: messages
            .filter((m) => !m.loading && m.content)
            .map(({ role, content }) => ({ role, content })),
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        const detail = data.detail;
        throw new Error(typeof detail === "string" ? detail : `Expand failed (${res.status})`);
      }
      const payload = data as {
        answer?: string;
        research?: MultiSourceResearchResult;
      };
      if (payload.research) {
        setResult(payload.research);
        const prefer = preferSourceTab(payload.research);
        if (prefer) setSourceTab(prefer);
      }
      setMessages((prev) =>
        prev.map((m) => {
          if (m.id !== messageId) {
            return payload.research ? { ...m, showSources: false } : m;
          }
          return {
            ...m,
            loading: false,
            proposal: undefined,
            content: payload.answer ?? "Search complete.",
            showSources: Boolean(payload.research),
            sourcesCollapsed: runMode === "plan",
          };
        }),
      );
    } catch (e) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === messageId
            ? {
                ...m,
                loading: false,
                proposalStatus: "pending" as const,
                content: e instanceof Error ? e.message : "Expand failed",
              }
            : m,
        ),
      );
    } finally {
      setExpanding(false);
    }
  };

  const dismissProposal = (messageId: string) => {
    setMessages((prev) =>
      prev.map((m) =>
        m.id === messageId ? { ...m, proposalStatus: "dismissed" as const } : m,
      ),
    );
  };

  const dismissModeProposal = (messageId: string) => {
    setMessages((prev) =>
      prev.map((m) =>
        m.id === messageId ? { ...m, modeProposalStatus: "dismissed" as const } : m,
      ),
    );
  };

  const generateReport = async (forceRefresh = false) => {
    if (!result) return;
    setReportBusy(true);
    setExportError(null);
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

  const routing = result?.routing ?? pendingRouting;

  const resetHome = () => {
    saveActiveSession();
    setView("home");
    setError(null);
    setMessages([]);
    setResult(null);
    setSessionLoading(false);
    setActiveSessionId(null);
    setTopic("");
    setChatInput("");
    setSourceTab(null);
  };

  const startNewChat = () => {
    saveActiveSession();
    resetHome();
  };

  const loadSession = (id: string) => {
    if (id === activeSessionId) return;
    saveActiveSession();
    const s = getChatSession(id);
    if (!s) return;
    sessionCreatedAtRef.current = s.createdAt;
    setActiveSessionId(s.id);
    setTopic(s.topic);
    setRunMode(s.runMode);
    let restored = s.messages;
    if (s.result && !restored.some((m) => m.showSources)) {
      const lastAssist = restored.map((m) => m.role).lastIndexOf("assistant");
      if (lastAssist >= 0) {
        restored = restored.map((m, i) =>
          i === lastAssist
            ? {
                ...m,
                showSources: true,
                sourcesCollapsed: s.runMode === "plan" || Boolean(m.plan),
              }
            : m,
        );
      }
    }
    setMessages(restored);
    setResult(s.result as MultiSourceResearchResult | null);
    setSourceTab(s.sourceTab);
    setChatInput("");
    setError(null);
    setSessionLoading(false);
    setView(s.messages.length > 0 ? "session" : "home");
  };

  const handleDeleteSession = (id: string) => {
    deleteChatSession(id);
    refreshSessions();
    if (activeSessionId === id) {
      setActiveSessionId(null);
      setView("home");
      setMessages([]);
      setResult(null);
      setTopic("");
    }
  };

  return (
    <div className="app-root">
      <div className="tech-bg" aria-hidden>
        <div className="tech-bg-grid" />
        <div className="tech-bg-glow" />
      </div>
      <div className="bg-grain" aria-hidden />
      <div
        ref={cursorRef}
        className={`app-cursor${cursorOn ? " is-on" : ""}`}
        aria-hidden
      >
        <span className="app-cursor-ring" />
        <span className="app-cursor-dot" />
      </div>
      <div className="app-shell">
        <ChatSidebar
          sessions={sessions}
          activeId={activeSessionId}
          open={sidebarOpen}
          onNewChat={startNewChat}
          onSelect={loadSession}
          onDelete={handleDeleteSession}
          onToggle={() => setSidebarOpen((o) => !o)}
        />

        <div className="app-main">
      <header className="site-header">
        <div className="site-header-inner">
          <button
            type="button"
            className="site-brand"
            onClick={startNewChat}
          >
            <AtelierMark size={16} className="site-brand-glyph" />
            Atelier
          </button>

          <nav className="site-nav" aria-label="Primary">
            {view === "session" && result && (
              <span className="site-nav-topic">{result.topic}</span>
            )}
          </nav>

          <div className="site-header-actions">
            {view === "session" && result && (
              <button
                type="button"
                className="btn-3d-ghost site-header-btn"
                onClick={() => {
                  setTopic(result.topic);
                  void runResearch(true);
                }}
              >
                Refresh
              </button>
            )}
          </div>
        </div>
      </header>

      <GeminiThread
        isHome={view === "home"}
        topic={topic}
        runMode={runMode}
        messages={messages}
        input={chatInput}
        busy={chatBusy}
        expanding={expanding}
        loadingResearch={sessionLoading}
        result={result}
        routing={routing}
        sourceTab={sourceTab}
        loadStage={loadStage}
        onTopicChange={setTopic}
        onRunModeChange={setRunMode}
        onInputChange={setChatInput}
        onSubmit={() => void runResearch()}
        onSend={() => void sendFollowUp()}
        onAllowOnce={(id) => void runExpand(id, "once")}
        onAllowAlways={(id) => void runExpand(id, "always")}
        onDismissProposal={dismissProposal}
        onAllowModeOnce={(id) => void runModeSwitch(id, "once")}
        onAllowModeAlways={(id) => void runModeSwitch(id, "always")}
        onDismissModeProposal={dismissModeProposal}
        onSourceTabChange={setSourceTab}
      />

      {error && (
        <p
          style={{
            maxWidth: "var(--content-max)",
            margin: "1rem auto",
            padding: "0 1rem",
            color: "var(--warn)",
            fontSize: "0.9rem",
          }}
        >
          {error}
        </p>
      )}
        </div>
      </div>
    </div>
  );
}
