"use client";

import { useMemo, useState } from "react";
import { formatSources } from "../lib/productConfig";
import {
  DISPLAY_TAB_LABELS,
  displayTabsForPartition,
  itemsForTab,
  partitionResults,
  type DisplayTab,
} from "../lib/partitionResults";
import { resolveThumbDisplay } from "../lib/sourceThumb";
import type { ResearchRoutingPlan } from "../lib/productTypes";
import SourceThumb from "./SourceThumb";

export interface ResearchItem {
  title: string;
  url: string;
  content: string;
  source: "tavily" | "news" | "papers" | "github";
  score: number | null;
  published: string | null;
  authors: string[] | null;
  venue: string | null;
  citation_count: number | null;
  image_url?: string | null;
  favicon_url?: string | null;
}

export interface MultiSourceResearchResult {
  topic: string;
  routing?: ResearchRoutingPlan | null;
  sources_used?: string[];
  tavily_results: ResearchItem[];
  news_results: ResearchItem[];
  papers_results: ResearchItem[];
  github_results?: ResearchItem[];
  tavily_answer: string | null;
  errors: Record<string, string>;
  cached?: boolean;
}

const TAB_HINTS: Record<DisplayTab, string> = {
  web: "Articles & docs",
  youtube: "Videos",
  github: "Repositories",
  news: "Headlines",
  papers: "Academic",
};

function hostnameOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function EvidenceCard({
  item,
  index,
  tab,
}: {
  item: ResearchItem;
  index: number;
  tab: DisplayTab;
}) {
  const tabLabel = DISPLAY_TAB_LABELS[tab];
  const thumb = resolveThumbDisplay(tab, item);

  return (
    <article className="evidence-card rise" style={{ animationDelay: `${Math.min(index, 8) * 0.04}s` }}>
      <a
        href={item.url}
        target="_blank"
        rel="noopener noreferrer"
        className="evidence-card-link"
        aria-label={`Open ${item.title}`}
      >
        <SourceThumb display={thumb} />

        <div className="evidence-card-body">
          <div className="evidence-card-top">
            <span className="evidence-pill">{tabLabel}</span>
            {item.score != null && tab === "web" ? (
              <span className="evidence-score">{item.score.toFixed(2)}</span>
            ) : null}
            {item.citation_count != null && tab === "github" ? (
              <span className="evidence-score">★ {item.citation_count.toLocaleString()}</span>
            ) : null}
          </div>

          <h3 className="evidence-title">{item.title}</h3>
          <p className="evidence-host">{hostnameOf(item.url)}</p>

          {item.content ? <p className="evidence-snippet">{item.content}</p> : null}

          {(item.published || item.venue || item.authors?.length) && (
            <p className="evidence-meta">
              {item.published ? `${item.published}` : ""}
              {item.venue ? `${item.published ? " · " : ""}${item.venue}` : ""}
              {item.authors?.length ? ` · ${item.authors.slice(0, 2).join(", ")}` : ""}
            </p>
          )}
        </div>
      </a>
    </article>
  );
}

export function sourceTabsForResult(result: MultiSourceResearchResult): DisplayTab[] {
  const p = partitionResults(result);
  const routed = result.routing?.sources?.length
    ? result.routing.sources
    : result.sources_used;
  return displayTabsForPartition(p, routed);
}

export default function SourcePanel({
  result,
  routing,
  tab,
  onTabChange,
}: {
  result: MultiSourceResearchResult;
  routing?: ResearchRoutingPlan | null;
  tab: DisplayTab | null;
  onTabChange: (tab: DisplayTab) => void;
}) {
  const partitioned = useMemo(() => partitionResults(result), [result]);
  const tabs = useMemo(
    () =>
      displayTabsForPartition(
        partitioned,
        routing?.sources?.length ? routing.sources : result.sources_used,
      ),
    [partitioned, routing, result.sources_used],
  );

  const activeTab = tab && tabs.includes(tab) ? tab : tabs[0] ?? null;
  const activeItems = activeTab ? itemsForTab(partitioned, activeTab) : [];

  const tabCounts: Record<DisplayTab, number> = {
    web: partitioned.web.length,
    youtube: partitioned.youtube.length,
    github: partitioned.github.length,
    news: partitioned.news.length,
    papers: partitioned.papers.length,
  };

  return (
    <div className="sources-pane sources-pane--v2 sources-pane--inline">
      <header className="evidence-header">
        <div>
          <p className="evidence-eyebrow">
            {routing ? formatSources(routing.sources) : "Research"} · {partitioned.total} sources
            {result.cached ? " · cached" : ""}
          </p>
          <h2 className="evidence-topic">{result.topic}</h2>
        </div>
      </header>

      {tabs.length > 0 && (
        <nav className="evidence-tabs" aria-label="Source types">
          {tabs.map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => onTabChange(key)}
              className={`evidence-tab${activeTab === key ? " is-active" : ""}`}
            >
              <span className="evidence-tab-label">{DISPLAY_TAB_LABELS[key]}</span>
              <span className="evidence-tab-count">{tabCounts[key]}</span>
              <span className="evidence-tab-hint">{TAB_HINTS[key]}</span>
            </button>
          ))}
        </nav>
      )}

      <p className="evidence-tab-desc">
        {activeTab ? `${activeItems.length} ${TAB_HINTS[activeTab].toLowerCase()} — click any card to open` : ""}
      </p>

      <div className="evidence-grid">
        {activeItems.length === 0 ? (
          <p className="sources-empty">No sources in this tab yet.</p>
        ) : (
          activeItems.map((item, i) => (
            <EvidenceCard key={`${item.url}-${i}`} item={item} index={i} tab={activeTab!} />
          ))
        )}
      </div>
    </div>
  );
}
