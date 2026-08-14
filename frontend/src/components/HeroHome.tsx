"use client";

const CAPABILITIES = [
  {
    title: "Research topics",
    body: "Pull live context from the open web before you draft a word.",
  },
  {
    title: "Read the news",
    body: "Surface what's trending today so the report stays timely.",
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

const MARQUEE = [
  "Tavily",
  "Google News",
  "Semantic Scholar",
  "OpenAlex",
  "Crossref",
  "arXiv",
  "Reports",
  "Exports",
];

export default function HeroHome({ onResearch }: { onResearch: () => void }) {
  return (
    <main className="fade-in hero-shell">
      <div className="hero-inner">
        <section className="hero-grid">
          <div className="hero-copy">
            <p className="hero-kicker rise">Field notes · Web · News · Papers</p>
            <h1 className="hero-title rise" style={{ animationDelay: "0.05s" }}>
              Atelier
            </h1>
            <div className="hero-brand-rule" aria-hidden />
            <p className="hero-subhead rise" style={{ animationDelay: "0.1s" }}>
              Your research desk, open
            </p>
            <p className="hero-lead rise" style={{ animationDelay: "0.14s" }}>
              One brief pulls live web pages, headlines, and academic papers —
              then writes a full research report you can browse and cite.
            </p>
            <div className="hero-actions rise" style={{ animationDelay: "0.18s" }}>
              <button type="button" className="btn-3d" onClick={onResearch}>
                Start research
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
              <p className="desk-front-title">Topic brief → ranked sources</p>
              <div className="doc-line" />
              <div className="doc-line" />
              <div className="doc-line short" />
              <div className="doc-line" />
              <p className="desk-front-meta">ATLAS DOSSIER · LIVE</p>
            </div>
            <div className="desk-pins">
              <span className="pin">Web</span>
              <span className="pin">News</span>
              <span className="pin">Papers</span>
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

        <section id="capabilities" className="hero-capabilities">
          <p className="hero-kicker">Instruments on the desk</p>
          <div className="cap-grid">
            {CAPABILITIES.map((cap, i) => (
              <button
                key={cap.title}
                type="button"
                className="cap-card rise"
                onClick={onResearch}
                style={{ animationDelay: `${0.08 + i * 0.05}s` }}
              >
                <p className="cap-index">{String(i + 1).padStart(2, "0")}</p>
                <p className="cap-title">{cap.title}</p>
                <p className="cap-body">{cap.body}</p>
              </button>
            ))}
          </div>

          <div className="hero-footer-cta">
            <div>
              <p className="hero-footer-title">Clear the desk. Start a brief.</p>
              <p className="hero-footer-body">Research → sources → report when you’re ready.</p>
            </div>
            <button type="button" className="btn-3d" onClick={onResearch}>
              Research
            </button>
          </div>
        </section>
      </div>
    </main>
  );
}
