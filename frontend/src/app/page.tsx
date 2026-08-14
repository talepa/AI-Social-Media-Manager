"use client";

/**
 * Interactive research product UI:
 * Hero → Research studio → Loader → Categorised results
 */

import { useEffect, useMemo, useRef, useState } from "react";

const API_BASE = "http://localhost:8001";

type View = "hero" | "studio" | "loading" | "results";
type SourceKey = "tavily" | "news" | "papers";
type TabKey = "overview" | SourceKey;

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
}

interface MultiSourceResearchResult {
  topic: string;
  tavily_results: ResearchItem[];
  news_results: ResearchItem[];
  papers_results: ResearchItem[];
  tavily_answer: string | null;
  errors: Record<string, string>;
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
    tool: "Semantic Scholar · OpenAlex",
    method: "Academic research — abstracts, authors, venues, citations.",
    index: "03",
  },
};

const CAPABILITIES = [
  {
    title: "Research topics",
    body: "Pull live context from the open web before you draft a word.",
  },
  {
    title: "Read the news",
    body: "Surface what’s trending today so your posts stay timely.",
  },
  {
    title: "Scan articles & papers",
    body: "Ground ideas in journalism and academic sources, not guesses.",
  },
  {
    title: "Write for social",
    body: "Turn findings into platform-ready posts — coming next in the pipeline.",
  },
] as const;

const LOAD_STAGES = [
  { label: "Scanning the web", tool: "Tavily" },
  { label: "Collecting headlines", tool: "Google News" },
  { label: "Reading papers", tool: "OpenAlex / S2" },
  { label: "Organising findings", tool: "LangGraph" },
];

const EXAMPLE_TOPICS = [
  "AI agents for founders",
  "LinkedIn thought leadership 2026",
  "Climate tech funding news",
  "Remote work productivity research",
];

function hostnameOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function Finding({ item, index }: { item: ResearchItem; index: number }) {
  const [open, setOpen] = useState(index === 0);
  const meta = SOURCE_META[item.source];

  return (
    <article
      className={`finding-row rise${open ? " is-open" : ""}`}
      style={{
        animationDelay: `${Math.min(index, 8) * 0.03}s`,
        borderBottom: "1px solid var(--line)",
      }}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        style={{
          width: "100%",
          textAlign: "left",
          border: "none",
          background: "transparent",
          padding: "1.35rem 0.35rem",
          cursor: "pointer",
          color: "inherit",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: "1rem",
            marginBottom: "0.45rem",
            flexWrap: "wrap",
          }}
        >
          <span
            style={{
              fontSize: "0.66rem",
              letterSpacing: "0.16em",
              textTransform: "uppercase",
              color: "var(--muted)",
            }}
          >
            {String(index + 1).padStart(2, "0")} · {meta.tool}
          </span>
          <span style={{ fontSize: "0.72rem", color: "var(--muted)" }}>
            {open ? "Hide" : "Read"} · {hostnameOf(item.url)}
          </span>
        </div>
        <h3
          style={{
            margin: 0,
            fontFamily: "var(--font-display)",
            fontSize: "clamp(1.2rem, 2vw, 1.55rem)",
            fontWeight: 500,
            lineHeight: 1.3,
            letterSpacing: "-0.01em",
          }}
        >
          {item.title}
        </h3>
      </button>

      {open && (
        <div className="fade-in" style={{ padding: "0 0.35rem 1.4rem" }}>
          <p style={{ margin: 0, fontSize: "0.78rem", color: "var(--muted)" }}>
            {item.published ? `${item.published} · ` : ""}
            {item.citation_count != null ? `${item.citation_count} citations · ` : ""}
            {item.score != null ? `relevance ${item.score.toFixed(2)} · ` : ""}
            {item.authors?.length ? item.authors.join(" · ") : ""}
            {item.venue ? ` — ${item.venue}` : ""}
          </p>
          {item.content ? (
            <p
              style={{
                margin: "0.75rem 0 1rem",
                fontSize: "0.95rem",
                lineHeight: 1.7,
                color: "var(--ink-soft)",
                maxWidth: "40rem",
              }}
            >
              {item.content}
            </p>
          ) : null}
          <a
            href={item.url}
            target="_blank"
            rel="noreferrer"
            style={{
              fontSize: "0.72rem",
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              borderBottom: "1px solid var(--ink)",
              textDecoration: "none",
              paddingBottom: 2,
            }}
          >
            Open source
          </a>
        </div>
      )}
    </article>
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
  const [loadStage, setLoadStage] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MultiSourceResearchResult | null>(null);
  const [tab, setTab] = useState<TabKey>("overview");
  const inputRef = useRef<HTMLInputElement>(null);

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
    ];
    return () => timers.forEach(clearTimeout);
  }, [view]);

  useEffect(() => {
    if (view !== "results" || !result) return;
    const order: TabKey[] = ["overview", "tavily", "news", "papers"];
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
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
  }, [view, result, tab]);

  const runResearch = async () => {
    if (!topic.trim()) return;
    setView("loading");
    setError(null);
    setResult(null);
    setTab("overview");
    try {
      const res = await fetch(`${API_BASE}/api/research/multi`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: topic.trim(), limit }),
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

  const totals = useMemo(() => {
    if (!result) return null;
    return {
      web: result.tavily_results.length,
      news: result.news_results.length,
      papers: result.papers_results.length,
      all:
        result.tavily_results.length +
        result.news_results.length +
        result.papers_results.length,
    };
  }, [result]);

  const activeItems: ResearchItem[] = useMemo(() => {
    if (!result) return [];
    if (tab === "tavily") return result.tavily_results;
    if (tab === "news") return result.news_results;
    if (tab === "papers") return result.papers_results;
    return [];
  }, [result, tab]);

  return (
    <div style={{ minHeight: "100vh" }}>
      {/* Persistent brand strip */}
      <header
        style={{
          maxWidth: 1080,
          margin: "0 auto",
          padding: "1.35rem clamp(1.25rem, 4vw, 2rem)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <button
          type="button"
          onClick={() => {
            setView("hero");
            setError(null);
          }}
          style={{
            border: "none",
            background: "transparent",
            padding: 0,
            cursor: "pointer",
            fontFamily: "var(--font-display)",
            fontSize: "1.55rem",
            fontWeight: 500,
            letterSpacing: "-0.02em",
            color: "var(--ink)",
          }}
        >
          Atelier
        </button>
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          {view !== "hero" && view !== "loading" && (
            <button
              type="button"
              className="btn-3d-ghost"
              style={{ padding: "0.7rem 1rem" }}
              onClick={() => setView("hero")}
            >
              Home
            </button>
          )}
          {view === "hero" && (
            <button type="button" className="btn-3d" onClick={() => setView("studio")}>
              Research
            </button>
          )}
        </div>
      </header>

      {/* HERO */}
      {view === "hero" && (
        <main
          className="fade-in"
          style={{
            maxWidth: 1100,
            margin: "0 auto",
            padding: "0 clamp(1.25rem, 4vw, 2rem) 4.5rem",
          }}
        >
          <section className="hero-grid">
            <div>
              <p
                style={{
                  margin: "0 0 1.25rem",
                  fontSize: "0.7rem",
                  letterSpacing: "0.22em",
                  textTransform: "uppercase",
                  color: "var(--muted)",
                }}
              >
                Field notes · Web · News · Papers
              </p>
              <h1
                style={{
                  margin: 0,
                  fontFamily: "var(--font-display)",
                  fontSize: "clamp(2.9rem, 7.2vw, 5.1rem)",
                  fontWeight: 500,
                  letterSpacing: "-0.035em",
                  lineHeight: 0.94,
                  maxWidth: "10ch",
                }}
              >
                Your research desk, open
              </h1>
              <p
                style={{
                  margin: "1.5rem 0 0",
                  maxWidth: "28rem",
                  fontSize: "1.05rem",
                  lineHeight: 1.65,
                  color: "var(--ink-soft)",
                }}
              >
                One brief pulls live web pages, headlines, and academic papers —
                then stacks them into a dossier you can browse by category before
                you write.
              </p>
              <div style={{ display: "flex", gap: "0.85rem", marginTop: "2.25rem", flexWrap: "wrap" }}>
                <button type="button" className="btn-3d" onClick={() => setView("studio")}>
                  Research
                </button>
                <button
                  type="button"
                  className="btn-3d-ghost"
                  onClick={() => {
                    document.getElementById("capabilities")?.scrollIntoView({ behavior: "smooth" });
                  }}
                >
                  See instruments
                </button>
              </div>
            </div>

            <div className="research-desk" aria-hidden>
              <div className="desk-surface" />
              <div className="doc-stack back">
                <span className="doc-tag">Papers</span>
                <div className="doc-line" />
                <div className="doc-line" />
                <div className="doc-line short" />
                <div className="doc-line" />
                <div className="doc-line short" />
              </div>
              <div className="doc-stack mid">
                <span className="doc-tag">News</span>
                <div className="doc-line" />
                <div className="doc-line short" />
                <div className="doc-line" />
                <div className="doc-line" />
                <div className="doc-line short" />
              </div>
              <div className="doc-stack front">
                <span className="doc-tag">Web · Tavily</span>
                <p
                  style={{
                    margin: "0 0 0.85rem",
                    fontFamily: "var(--font-display)",
                    fontSize: "1.35rem",
                    lineHeight: 1.2,
                    fontWeight: 500,
                  }}
                >
                  Topic brief → ranked sources
                </p>
                <div className="doc-line" />
                <div className="doc-line" />
                <div className="doc-line short" />
                <div className="doc-line" />
                <p style={{ margin: "1rem 0 0", fontSize: "0.72rem", color: "var(--muted)", letterSpacing: "0.08em" }}>
                  ATLAS DOSSIER · LIVE
                </p>
              </div>
              <div className="desk-pins">
                <span className="pin">Web</span>
                <span className="pin">News</span>
                <span className="pin">Papers</span>
              </div>
            </div>
          </section>

          <section id="capabilities" style={{ paddingTop: "3.5rem" }}>
            <p
              style={{
                margin: "0 0 1.75rem",
                fontSize: "0.7rem",
                letterSpacing: "0.18em",
                textTransform: "uppercase",
                color: "var(--muted)",
              }}
            >
              Instruments on the desk
            </p>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                gap: "1.75rem",
              }}
            >
              {CAPABILITIES.map((cap, i) => (
                <button
                  key={cap.title}
                  type="button"
                  className="cap-card rise"
                  onClick={() => setView("studio")}
                  style={{
                    animationDelay: `${i * 0.04}s`,
                    textAlign: "left",
                    border: "none",
                    borderTop: "1px solid var(--ink)",
                    background: "transparent",
                    padding: "1.1rem 0 0",
                    cursor: "pointer",
                    color: "inherit",
                    width: "100%",
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
                    {String(i + 1).padStart(2, "0")}
                  </p>
                  <p
                    style={{
                      margin: "0.5rem 0 0",
                      fontFamily: "var(--font-display)",
                      fontSize: "1.45rem",
                      fontWeight: 500,
                    }}
                  >
                    {cap.title}
                  </p>
                  <p style={{ margin: "0.55rem 0 0", fontSize: "0.9rem", lineHeight: 1.55, color: "var(--ink-soft)" }}>
                    {cap.body}
                  </p>
                </button>
              ))}
            </div>

            <div
              style={{
                marginTop: "3.5rem",
                padding: "2rem 0",
                borderTop: "1px solid var(--ink)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: "1.5rem",
                flexWrap: "wrap",
              }}
            >
              <div>
                <p
                  style={{
                    margin: 0,
                    fontFamily: "var(--font-display)",
                    fontSize: "clamp(1.5rem, 3vw, 2rem)",
                    fontWeight: 500,
                    letterSpacing: "-0.02em",
                  }}
                >
                  Clear the desk. Start a brief.
                </p>
                <p style={{ margin: "0.4rem 0 0", color: "var(--muted)", fontSize: "0.9rem" }}>
                  Research → loader → category dossier.
                </p>
              </div>
              <button type="button" className="btn-3d" onClick={() => setView("studio")}>
                Research
              </button>
            </div>
          </section>
        </main>
      )}

      {/* STUDIO — open research sheet */}
      {view === "studio" && (
        <main
          className="sheet-up"
          style={{
            maxWidth: 720,
            margin: "0 auto",
            padding: "1rem clamp(1.25rem, 4vw, 2rem) 4rem",
            minHeight: "75vh",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
          }}
        >
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
            We’ll search the web, pull news, and scan papers — then open your dossier by category.
          </p>

          <label
            htmlFor="topic"
            style={{
              display: "block",
              marginTop: "2.5rem",
              fontSize: "0.68rem",
              letterSpacing: "0.16em",
              textTransform: "uppercase",
              color: "var(--muted)",
            }}
          >
            Brief
          </label>
          <input
            ref={inputRef}
            id="topic"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && runResearch()}
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
              {EXAMPLE_TOPICS.map((ex) => (
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
                onClick={runResearch}
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
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: "0.75rem",
              marginTop: "3rem",
              borderTop: "1px solid var(--line)",
              paddingTop: "1.5rem",
            }}
          >
            {(Object.keys(SOURCE_META) as SourceKey[]).map((key) => (
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
                Dossier · {totals.all} findings
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
            <button
              type="button"
              className="btn-3d-ghost"
              style={{ padding: "0.75rem 1.1rem" }}
              onClick={() => setView("studio")}
            >
              New research
            </button>
          </div>

          <nav className="cat-rail" aria-label="Categories">
            {(
              [
                ["overview", "Overview", totals.all, totals.all],
                ["tavily", "Web", totals.web, totals.all],
                ["news", "News", totals.news, totals.all],
                ["papers", "Papers", totals.papers, totals.all],
              ] as const
            ).map(([key, label, count, max]) => {
              const pct = max > 0 ? Math.max(8, Math.round((count / max) * 100)) : 0;
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
          <p
            style={{
              margin: "-0.75rem 0 1.25rem",
              fontSize: "0.72rem",
              color: "var(--muted)",
            }}
          >
            Click a category · ← → keys to switch
          </p>

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
              <p style={{ margin: "0 0 1.15rem", color: "var(--ink-soft)", lineHeight: 1.6 }}>
                Jump into a stack. Each card shows a preview of what’s inside.
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
                  ] as const
                ).map(([key, count, items]) => {
                  const m = SOURCE_META[key];
                  return (
                    <button
                      key={key}
                      type="button"
                      className="source-card"
                      onClick={() => setTab(key)}
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
                        {m.tool}
                      </p>
                      <p
                        style={{
                          margin: "0.45rem 0 0",
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
            </div>
          )}

          {tab !== "overview" && (
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
                <div style={{ display: "flex", gap: "0.45rem" }}>
                  <button
                    type="button"
                    className="btn-3d-ghost"
                    style={{ padding: "0.55rem 0.85rem" }}
                    onClick={() => {
                      const order: TabKey[] = ["overview", "tavily", "news", "papers"];
                      const i = order.indexOf(tab);
                      setTab(order[(i - 1 + order.length) % order.length]);
                    }}
                  >
                    ←
                  </button>
                  <button
                    type="button"
                    className="btn-3d-ghost"
                    style={{ padding: "0.55rem 0.85rem" }}
                    onClick={() => {
                      const order: TabKey[] = ["overview", "tavily", "news", "papers"];
                      const i = order.indexOf(tab);
                      setTab(order[(i + 1) % order.length]);
                    }}
                  >
                    →
                  </button>
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
              <div className="panel-scroll">
                {activeItems.length === 0 ? (
                  <p style={{ color: "var(--muted)" }}>No findings in this category.</p>
                ) : (
                  activeItems.map((item, i) => (
                    <Finding key={`${item.url}-${i}`} item={item} index={i} />
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
