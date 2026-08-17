"use client";

const QUERIES = [
  {
    topic: "LangGraph multi-agent orchestration",
    kind: "AI Engineer",
    web: 8,
    news: 0,
    papers: 6,
    github: 8,
    delta: "+4",
  },
  {
    topic: "B2B SaaS pricing 2026",
    kind: "Founder",
    web: 8,
    news: 7,
    papers: 4,
    github: 0,
    delta: "+2",
  },
  {
    topic: "Transformer attention mechanisms",
    kind: "Academic",
    web: 5,
    news: 0,
    papers: 8,
    github: 0,
    delta: "+6",
  },
  {
    topic: "EU AI Act enforcement",
    kind: "News desk",
    web: 6,
    news: 8,
    papers: 3,
    github: 0,
    delta: "0",
  },
  {
    topic: "vLLM inference optimization",
    kind: "AI Engineer",
    web: 6,
    news: 0,
    papers: 5,
    github: 8,
    delta: "+3",
  },
  {
    topic: "Climate tech funding news",
    kind: "General",
    web: 7,
    news: 8,
    papers: 3,
    github: 0,
    delta: "+1",
  },
] as const;

const LOGOS = [
  "Tavily",
  "Google News",
  "GitHub",
  "Semantic Scholar",
  "OpenAlex",
  "Crossref",
  "arXiv",
  "LangGraph",
];

const FLOW = [
  {
    step: "01",
    title: "Get started",
    body: "Enter a topic and pick a research type. Atelier chooses the right mix of web, news, papers, and GitHub.",
  },
  {
    step: "02",
    title: "Take action",
    body: "Browse ranked findings as cards or a list — previews, scores, citations, and a news timeline.",
  },
  {
    step: "03",
    title: "Get the report",
    body: "Compile a cited briefing with findings, gaps, and exports — Markdown, JSON, or PDF.",
  },
] as const;

const FEATURES = [
  {
    id: "web",
    index: "01",
    kicker: "Web",
    title: "Live pages, ranked.",
    body: "Tavily searches the open web and returns titles, snippets, and relevance scores — the first pass before you write a word.",
    tool: "Tavily Search",
    flip: false,
    metrics: [
      ["Relevance", "0.92"],
      ["Pages", "8"],
      ["Latency", "live"],
    ],
  },
  {
    id: "news",
    index: "02",
    kicker: "News",
    title: "Today’s wire, cited.",
    body: "Public news feeds surface timely headlines linked to publisher pages, so the briefing stays current — not a week old.",
    tool: "Google News",
    flip: true,
    metrics: [
      ["Headlines", "8"],
      ["Freshness", "today"],
      ["Publishers", "open"],
    ],
  },
  {
    id: "papers",
    index: "03",
    kicker: "Papers",
    title: "Scholarship, merged.",
    body: "Semantic Scholar, OpenAlex, Crossref, and arXiv run in parallel, then dedupe by title and DOI — abstracts, venues, citations.",
    tool: "S2 · OpenAlex · arXiv",
    flip: false,
    metrics: [
      ["Libraries", "4"],
      ["Citations", "ranked"],
      ["Deduped", "DOI"],
    ],
  },
  {
    id: "github",
    index: "04",
    kicker: "GitHub",
    title: "Code as evidence.",
    body: "For engineer-style research, starred public repos sit beside papers — language, topics, and owner context on the same desk.",
    tool: "GitHub Search",
    flip: true,
    metrics: [
      ["Sort", "stars"],
      ["Repos", "8"],
      ["Scope", "public"],
    ],
  },
] as const;

const DELIVERABLES = [
  { title: "Executive summary", note: "2–4 short paragraphs" },
  { title: "Ranked findings", note: "Why it matters" },
  { title: "News highlights", note: "Timely coverage" },
  { title: "Academic context", note: "Papers & venues" },
  { title: "Open questions", note: "Gaps to chase" },
  { title: "Source list", note: "MD · JSON · PDF" },
] as const;

const PROOF = [
  {
    title: "Sources first",
    body: "The report is compiled from what was actually retrieved — not a free-form essay with invented citations.",
  },
  {
    title: "On demand",
    body: "Search once, then generate the briefing when you need it. Fast compile by default, Gemini when you want a sharper pass.",
  },
  {
    title: "Export ready",
    body: "Take the work with you — Markdown, JSON, or a printable PDF — with the source list attached.",
  },
] as const;

function QueryCard({
  topic,
  kind,
  web,
  news,
  papers,
  github,
  delta,
}: (typeof QUERIES)[number]) {
  const total = web + news + papers + github;
  const rows = [
    web ? ["Web", web] : null,
    news ? ["News", news] : null,
    papers ? ["Papers", papers] : null,
    github ? ["GitHub", github] : null,
  ].filter(Boolean) as [string, number][];

  return (
    <article className="query-card">
      <div className="query-card-top">
        <span>Analysis</span>
        <span className="query-live">Live</span>
      </div>
      <h3 className="query-card-title">{topic}</h3>
      <p className="query-card-kind">{kind}</p>
      <div className="query-metrics">
        {rows.map(([label, value]) => (
          <div key={label} className="query-metric">
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
        <div className="query-metric">
          <span>Sources</span>
          <strong>
            {total}
            <em>{delta}</em>
          </strong>
        </div>
      </div>
    </article>
  );
}

function FeatureMock({
  tool,
  metrics,
}: {
  tool: string;
  metrics: readonly (readonly [string, string])[];
}) {
  return (
    <div className="feature-mock" aria-hidden>
      <div className="feature-mock-bar">
        <span>{tool}</span>
        <span>Preview</span>
      </div>
      <div className="feature-mock-body">
        {metrics.map(([label, value]) => (
          <div key={label} className="feature-mock-row">
            <span>{label}</span>
            <b>{value}</b>
            <i style={{ width: value.match(/^\d/) ? "72%" : "48%" }} />
          </div>
        ))}
      </div>
    </div>
  );
}

export default function HeroHome({ onResearch }: { onResearch: () => void }) {
  const feed = [...QUERIES, ...QUERIES];

  return (
    <main className="fade-in hero-shell">
      <section className="atelier-hero">
        <div className="hero-inner atelier-hero-grid">
          <div className="atelier-hero-copy">
            <p className="hero-kicker rise">Research desk · 2026</p>
            <h1 className="atelier-hero-title rise" style={{ animationDelay: "0.05s" }}>
              Get a cited report from live sources.
            </h1>
            <p className="atelier-hero-lead rise" style={{ animationDelay: "0.1s" }}>
              Search the web, headlines, papers, and GitHub in parallel — then
              turn the findings into a briefing you can browse, cite, and download.
            </p>
            <div className="hero-actions rise" style={{ animationDelay: "0.16s" }}>
              <button type="button" className="btn-3d" onClick={onResearch}>
                Start research
              </button>
              <button
                type="button"
                className="btn-3d-ghost"
                onClick={() => {
                  document.getElementById("how-it-works")?.scrollIntoView({
                    behavior: "smooth",
                  });
                }}
              >
                How it works
              </button>
            </div>
          </div>

          <div className="query-feed" aria-hidden>
            <div className="query-feed-fade query-feed-fade-top" />
            <div className="query-feed-track">
              {feed.map((q, i) => (
                <QueryCard key={`${q.topic}-${i}`} {...q} />
              ))}
            </div>
            <div className="query-feed-fade query-feed-fade-bot" />
          </div>
        </div>

        <div className="logo-marquee" aria-hidden>
          <div className="logo-marquee-track">
            {[...LOGOS, ...LOGOS].map((label, i) => (
              <span key={`${label}-${i}`}>{label}</span>
            ))}
          </div>
        </div>
      </section>

      <section id="how-it-works" className="section-band">
        <div className="hero-inner section-band-inner">
          <div className="hero-section-head">
            <p className="hero-kicker">Process</p>
            <h2 className="hero-section-title">Three steps. One desk.</h2>
            <p className="hero-section-lead">
              From a topic to a finished report — without leaving the page.
            </p>
          </div>
          <ol className="process-row">
            {FLOW.map((item) => (
              <li key={item.step}>
                <button type="button" className="process-cell" onClick={onResearch}>
                  <span className="process-num">{item.step}</span>
                  <h3>{item.title}</h3>
                  <p>{item.body}</p>
                </button>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section id="capabilities" className="section-band section-band-quiet">
        <div className="hero-inner section-band-inner">
          <div className="hero-section-head">
            <p className="hero-kicker">Sources</p>
            <h2 className="hero-section-title">
              Visibility across the open web, the news, papers, and code.
            </h2>
            <p className="hero-section-lead">
              One automated pass. Four instruments. A report when you ask for it.
            </p>
          </div>
        </div>

        {FEATURES.map((item) => (
          <article
            key={item.id}
            className={`feature-split${item.flip ? " is-flip" : ""}`}
          >
            <div className="hero-inner feature-split-inner">
              <div className="feature-split-copy">
                <p className="hero-kicker">
                  {item.index} · {item.kicker}
                </p>
                <h3 className="feature-split-title">{item.title}</h3>
                <p className="feature-split-body">{item.body}</p>
                <button type="button" className="text-link" onClick={onResearch}>
                  Research this source →
                </button>
              </div>
              <FeatureMock tool={item.tool} metrics={item.metrics} />
            </div>
          </article>
        ))}
      </section>

      <section id="report" className="section-band">
        <div className="hero-inner section-band-inner report-split">
          <div>
            <p className="hero-kicker">Report</p>
            <h2 className="hero-section-title">What’s in the briefing.</h2>
            <p className="hero-section-lead">
              Fast compile by default, or enhance with Gemini when you want a
              sharper pass.
            </p>
            <ul className="deliver-list">
              {DELIVERABLES.map((item) => (
                <li key={item.title}>
                  <span>{item.title}</span>
                  <em>{item.note}</em>
                </li>
              ))}
            </ul>
            <div className="section-band-cta">
              <button type="button" className="btn-3d" onClick={onResearch}>
                Start research
              </button>
            </div>
          </div>
          <aside className="report-sheet" aria-hidden>
            <p className="report-sheet-kicker">Briefing · Compile</p>
            <p className="report-sheet-title">LangGraph agents</p>
            <p className="report-sheet-body">
              This briefing compiles 22 sources — web, papers, and GitHub —
              ranked from retrieved titles, snippets, and star signals.
            </p>
            <div className="report-sheet-bars">
              <span style={{ width: "82%" }} />
              <span style={{ width: "61%" }} />
              <span style={{ width: "74%" }} />
            </div>
            <p className="report-sheet-foot">MD · JSON · PDF</p>
          </aside>
        </div>
      </section>

      <section className="section-band section-band-quiet" aria-label="Why Atelier">
        <div className="hero-inner section-band-inner">
          <div className="hero-section-head">
            <p className="hero-kicker">Why</p>
            <h2 className="hero-section-title">Proof, not padding.</h2>
          </div>
          <div className="proof-row">
            {PROOF.map((item) => (
              <article key={item.title} className="proof-cell">
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="close-band">
        <div className="hero-inner close-band-inner">
          <div>
            <p className="hero-kicker">Studio</p>
            <p className="close-title">Ready to research?</p>
            <p className="close-body">
              Search sources first, then generate the report when you need it.
            </p>
          </div>
          <button type="button" className="btn-3d" onClick={onResearch}>
            Start research
          </button>
        </div>
      </section>
    </main>
  );
}
