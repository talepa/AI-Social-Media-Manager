"use client";

const STAGES = [
  { label: "Routing your question", tool: "Topic router" },
  { label: "Scanning the web", tool: "Tavily" },
  { label: "Collecting headlines", tool: "News" },
  { label: "Reading papers", tool: "Academic" },
  { label: "Searching GitHub", tool: "Repos" },
  { label: "Organising findings", tool: "LangGraph" },
];

export default function ResearchProgress({
  topic,
  stageIndex,
  routingReason,
  routingSources,
}: {
  topic: string;
  stageIndex: number;
  routingReason?: string | null;
  routingSources?: string[] | null;
}) {
  const progress = Math.min(96, ((stageIndex + 1) / STAGES.length) * 100);

  return (
    <div className="research-progress gemini-in" aria-live="polite" aria-busy="true">
      <div className="research-progress-glow" aria-hidden />
      <div className="research-progress-inner">
        <div className="research-progress-head">
          <span className="research-progress-icon" aria-hidden>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
              <path d="M20 20l-3.5-3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </span>
          <div>
            <p className="research-progress-kicker">Deep research</p>
            <p className="research-progress-topic">“{topic}”</p>
          </div>
        </div>

        {routingReason ? (
          <p className="research-progress-routing">{routingReason}</p>
        ) : null}
        {routingSources?.length ? (
          <div className="research-progress-pills">
            {routingSources.map((s) => (
              <span key={s} className="research-progress-pill">
                {s}
              </span>
            ))}
          </div>
        ) : null}

        <div className="research-progress-bar" aria-hidden>
          <div className="research-progress-bar-fill" style={{ width: `${progress}%` }} />
        </div>

        <ul className="research-progress-stages">
          {STAGES.map((stage, i) => {
            const done = i < stageIndex;
            const active = i === stageIndex;
            return (
              <li
                key={stage.label}
                className={`research-progress-stage${done ? " is-done" : ""}${active ? " is-active" : ""}`}
              >
                <span className="research-progress-stage-dot" aria-hidden />
                <span className="research-progress-stage-label">{stage.label}</span>
                <span className="research-progress-stage-tool">{stage.tool}</span>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
