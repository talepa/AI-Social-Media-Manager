"use client";

import type { CSSProperties } from "react";

const FLOW = [
  {
    step: "01",
    title: "Enter a topic",
    body: "Tell Atelier what you want to learn. Choose a research type — web, news, papers, or GitHub.",
  },
  {
    step: "02",
    title: "Review sources",
    body: "Browse findings as cards or a list — previews, scores, citations, and a news timeline.",
  },
  {
    step: "03",
    title: "Get the report",
    body: "Generate a structured report with findings, context, open questions, and sources.",
  },
] as const;

const INSTRUMENTS = [
  {
    index: "01",
    label: "Web",
    tool: "Tavily Search",
    body: "Ranked pages and snippets — the first pass across the open web.",
  },
  {
    index: "02",
    label: "News",
    tool: "Google News",
    body: "Fresh headlines linked to publisher pages so coverage stays current.",
  },
  {
    index: "03",
    label: "Papers",
    tool: "S2 · OpenAlex · Crossref · arXiv",
    body: "Academic results merged and deduped — abstracts, venues, citations.",
  },
  {
    index: "04",
    label: "GitHub",
    tool: "Repo search",
    body: "For engineer-style research — starred public repos with language and topics.",
  },
  {
    index: "05",
    label: "Report",
    tool: "Compile · Gemini",
    body: "Executive summary, ranked findings, and a source list you can export.",
  },
] as const;

const DELIVERABLES = [
  "Executive summary",
  "Ranked findings",
  "News highlights",
  "Academic context",
  "Open questions",
  "Source list",
  "MD · HTML · PDF",
];

const MARQUEE = [
  "Tavily",
  "Google News",
  "GitHub",
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
              From topic to report
            </p>
            <p className="hero-lead rise" style={{ animationDelay: "0.14s" }}>
              Search the live web, headlines, papers, and GitHub in one place —
              then turn the results into a report you can browse, cite, and download.
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
              <p className="desk-front-title">Topic → ranked sources</p>
              <div className="doc-line" />
              <div className="doc-line" />
              <div className="doc-line short" />
              <div className="doc-line" />
              <div className="desk-front-bars">
                <span style={{ width: "78%" }} />
                <span style={{ width: "54%" }} />
                <span style={{ width: "66%" }} />
              </div>
              <p className="desk-front-meta">RESEARCH · MULTI-SOURCE</p>
            </div>
            <div className="desk-pins">
              <span className="pin">Web</span>
              <span className="pin">News</span>
              <span className="pin">Papers</span>
            </div>
            <div className="desk-note">
              <p>Parallel search</p>
              <p>Page previews</p>
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

      <section id="how-it-works" className="section-band section-band-process">
        <div className="hero-inner section-band-inner">
          <div className="hero-section-head">
            <p className="hero-kicker">Process</p>
            <h2 className="hero-section-title">How research works</h2>
            <p className="hero-section-lead">
              Three steps from a topic to a finished report.
            </p>
          </div>
          <div className="step-card-grid">
            {FLOW.map((item, i) => (
              <button
                key={item.step}
                type="button"
                className="step-card"
                onClick={onResearch}
                style={{ "--float-delay": `${i * 0.35}s` } as CSSProperties}
              >
                <span className="step-card-num">{item.step}</span>
                <h3 className="step-card-title">{item.title}</h3>
                <p className="step-card-body">{item.body}</p>
                <span className="step-card-cta">Start →</span>
              </button>
            ))}
          </div>
        </div>
      </section>

      <section id="capabilities" className="section-band section-band-desk">
        <div className="hero-inner section-band-inner">
          <div className="hero-section-head">
            <p className="hero-kicker">Sources</p>
            <h2 className="hero-section-title">What Atelier searches</h2>
            <p className="hero-section-lead">
              Four tools on the desk — tap any card to start researching.
            </p>
          </div>
          <div className="feature-card-grid feature-card-grid-4">
            {INSTRUMENTS.map((item, i) => (
              <button
                key={item.label}
                type="button"
                className="feature-card feature-card-tall"
                onClick={onResearch}
                style={{ "--float-delay": `${0.15 + i * 0.28}s` } as CSSProperties}
              >
                <div className="feature-card-top">
                  <span className="feature-card-index">{item.index}</span>
                  <span className="feature-card-badge">{item.tool}</span>
                </div>
                <h3 className="feature-card-title">{item.label}</h3>
                <p className="feature-card-body">{item.body}</p>
                <span className="feature-card-cta">Research →</span>
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="section-band section-band-report" aria-label="Report contents">
        <div className="hero-inner section-band-inner">
          <div className="hero-section-head">
            <p className="hero-kicker">Report</p>
            <h2 className="hero-section-title">What’s in the report</h2>
            <p className="hero-section-lead">
              Fast compile by default, or enhance with Gemini when you want a sharper pass.
            </p>
          </div>
          <ul className="deliver-chip-grid">
            {DELIVERABLES.map((item, i) => (
              <li
                key={item}
                className="deliver-chip"
                style={{ "--float-delay": `${i * 0.18}s` } as CSSProperties}
              >
                {item}
              </li>
            ))}
          </ul>
          <div className="section-band-cta">
            <button type="button" className="btn-3d" onClick={onResearch}>
              Start research
            </button>
          </div>
        </div>
      </section>

      <div className="hero-inner">
        <div className="hero-footer-cta">
          <div>
            <p className="hero-footer-title">Ready to research?</p>
            <p className="hero-footer-body">
              Search sources first, then generate the report when you need it.
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
