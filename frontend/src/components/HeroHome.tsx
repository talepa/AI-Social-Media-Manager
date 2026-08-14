"use client";

import type { CSSProperties } from "react";

const KINETIC = [
  "Topic",
  "Web",
  "News",
  "Papers",
  "Preview",
  "Rank",
  "Report",
  "Cite",
  "Export",
];

const FLOW = [
  {
    step: "01",
    title: "Open a brief",
    body: "Name the topic. Atelier fans out to live web, news, and papers in one pass.",
  },
  {
    step: "02",
    title: "Read the stacks",
    body: "Browse cards or list — real previews, scores, citations, and a news timeline.",
  },
  {
    step: "03",
    title: "Compile the report",
    body: "A structured briefing with findings, context, open questions, and sources.",
  },
] as const;

const FEATURED = [
  {
    label: "Web",
    tool: "Tavily",
    body: "Ranked pages and snippets — the desk’s first pass across the open web.",
  },
  {
    label: "Report",
    tool: "Compile · Gemini",
    body: "Executive summary, ranked findings, and a citeable source list on demand.",
  },
] as const;

const SIDE_NOTES = [
  {
    label: "News",
    body: "Google News wire resolved to publisher pages so the brief stays timely.",
  },
  {
    label: "Papers",
    body: "Semantic Scholar, OpenAlex, Crossref, and arXiv — merged, not duplicated.",
  },
] as const;

const DELIVERABLES = [
  "Executive summary",
  "Ranked findings",
  "News highlights",
  "Academic context",
  "Open questions",
  "Source dossier",
  "MD · HTML · PDF",
];

const MARQUEE = [
  "Tavily",
  "Google News",
  "Semantic Scholar",
  "OpenAlex",
  "Crossref",
  "arXiv",
  "LangGraph",
];

export default function HeroHome({ onResearch }: { onResearch: () => void }) {
  return (
    <main className="fade-in hero-shell">
      <div className="hero-inner">
        <section className="hero-grid">
          <div className="hero-copy">
            <p className="hero-kicker rise">Research desk · Field notes</p>
            <h1 className="hero-title rise" style={{ animationDelay: "0.05s" }}>
              Atelier
            </h1>
            <div className="hero-brand-rule" aria-hidden />
            <p className="hero-subhead rise" style={{ animationDelay: "0.1s" }}>
              From topic to dossier
            </p>
            <p className="hero-lead rise" style={{ animationDelay: "0.14s" }}>
              One brief gathers the live web, today’s headlines, and academic papers —
              then shapes a report you can browse, cite, and export.
            </p>
            <div className="hero-actions rise" style={{ animationDelay: "0.18s" }}>
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

          <div className="research-desk" aria-hidden>
            <div className="desk-surface" />
            <div className="desk-lamp" />
            <div className="doc-stack back">
              <span className="doc-tag">Papers</span>
              <p className="desk-stack-label">Citation ledger</p>
              <div className="doc-line" />
              <div className="doc-line" />
              <div className="doc-line short" />
              <div className="doc-line" />
              <div className="doc-line short" />
              <div className="doc-line" />
            </div>
            <div className="doc-stack mid">
              <span className="doc-tag">News</span>
              <p className="desk-stack-label">Today’s wire</p>
              <div className="doc-line" />
              <div className="doc-line short" />
              <div className="doc-line" />
              <div className="doc-line" />
              <div className="doc-line short" />
            </div>
            <div className="doc-stack front">
              <div className="desk-front-top">
                <span className="doc-tag">Web · Tavily</span>
                <span className="desk-live">Live</span>
              </div>
              <p className="desk-front-title">Topic brief → ranked sources</p>
              <div className="doc-line" />
              <div className="doc-line" />
              <div className="doc-line short" />
              <div className="doc-line" />
              <div className="desk-front-bars">
                <span style={{ width: "78%" }} />
                <span style={{ width: "54%" }} />
                <span style={{ width: "66%" }} />
              </div>
              <p className="desk-front-meta">ATLAS DOSSIER · MULTI-SOURCE</p>
            </div>
            <div className="desk-pins">
              <span className="pin">Web</span>
              <span className="pin">News</span>
              <span className="pin">Papers</span>
            </div>
            <div className="desk-note">
              <p>Parallel gather</p>
              <p>Preview enrich</p>
              <p>Report on demand</p>
            </div>
          </div>
        </section>

        <div className="hero-marquee" aria-hidden>
          <div className="hero-marquee-track">
            {[...MARQUEE, ...MARQUEE].map((label, i) => (
              <span key={`${label}-${i}`}>{label}</span>
            ))}
          </div>
        </div>
      </div>

      {/* Full-bleed kinetic type */}
      <div className="moving-type" aria-hidden>
        <div className="moving-type-track moving-type-track-a">
          {[...KINETIC, ...KINETIC].map((word, i) => (
            <span key={`a-${word}-${i}`}>{word}</span>
          ))}
        </div>
        <div className="moving-type-track moving-type-track-b">
          {[...KINETIC].reverse().concat([...KINETIC].reverse()).map((word, i) => (
            <span key={`b-${word}-${i}`}>{word}</span>
          ))}
        </div>
      </div>

      <div className="hero-inner">
        {/* Process — editorial, not cards */}
        <section id="how-it-works" className="hero-section">
          <div className="hero-section-head">
            <p className="hero-kicker">Process</p>
            <h2 className="hero-section-title">How a brief moves</h2>
            <p className="hero-section-lead">
              Three beats. No dashboard — just the path from empty sheet to dossier.
            </p>
          </div>
          <ol className="process-ladder">
            {FLOW.map((item, i) => (
              <li
                key={item.step}
                className="process-rung rise"
                style={{ animationDelay: `${0.05 + i * 0.07}s` }}
              >
                <span className="process-num">{item.step}</span>
                <div className="process-copy">
                  <h3>{item.title}</h3>
                  <p>{item.body}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        {/* Instruments — only two animated cards + text notes */}
        <section id="capabilities" className="hero-section">
          <div className="hero-section-head">
            <p className="hero-kicker">Instruments</p>
            <h2 className="hero-section-title">What’s on the desk</h2>
            <p className="hero-section-lead">
              Two focal tools as floating cards. The rest of the desk as quiet notes.
            </p>
          </div>

          <div className="feature-mix">
            <div className="feature-card-grid feature-card-grid-2">
              {FEATURED.map((item, i) => (
                <button
                  key={item.label}
                  type="button"
                  className="feature-card feature-card-tall"
                  onClick={onResearch}
                  style={{ "--float-delay": `${i * 0.4}s` } as CSSProperties}
                >
                  <div className="feature-card-top">
                    <span className="feature-card-index">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span className="feature-card-badge">{item.tool}</span>
                  </div>
                  <h3 className="feature-card-title">{item.label}</h3>
                  <p className="feature-card-body">{item.body}</p>
                  <span className="feature-card-cta">Open brief →</span>
                </button>
              ))}
            </div>

            <div className="side-notes">
              {SIDE_NOTES.map((note) => (
                <button
                  key={note.label}
                  type="button"
                  className="side-note"
                  onClick={onResearch}
                >
                  <span className="side-note-label">{note.label}</span>
                  <span className="side-note-body">{note.body}</span>
                  <span className="side-note-go" aria-hidden>
                    →
                  </span>
                </button>
              ))}
            </div>
          </div>
        </section>
      </div>

      {/* Moving type for deliverables */}
      <section className="type-band" aria-label="Report contents">
        <div className="type-band-inner">
          <p className="hero-kicker">Inside the report</p>
          <p className="type-band-title">What leaves the desk</p>
        </div>
        <div className="moving-type moving-type-dense" aria-hidden>
          <div className="moving-type-track moving-type-track-a">
            {[...DELIVERABLES, ...DELIVERABLES].map((word, i) => (
              <span key={`d1-${word}-${i}`}>{word}</span>
            ))}
          </div>
          <div className="moving-type-track moving-type-track-b">
            {[...DELIVERABLES].reverse().concat([...DELIVERABLES].reverse()).map((word, i) => (
              <span key={`d2-${word}-${i}`}>{word}</span>
            ))}
          </div>
        </div>
        <div className="type-band-inner type-band-cta">
          <button type="button" className="btn-3d" onClick={onResearch}>
            Start research
          </button>
        </div>
      </section>

      <div className="hero-inner">
        <div className="hero-footer-cta">
          <div>
            <p className="hero-footer-title">Clear the desk. Start a brief.</p>
            <p className="hero-footer-body">
              Research → stacks → report when you’re ready.
            </p>
          </div>
          <button type="button" className="btn-3d" onClick={onResearch}>
            Research
          </button>
        </div>
      </div>
    </main>
  );
}
