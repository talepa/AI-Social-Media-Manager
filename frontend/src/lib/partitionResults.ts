import type { ResearchItem, MultiSourceResearchResult } from "../components/SourcePanel";

export type DisplayTab = "web" | "youtube" | "github" | "news" | "papers";

function host(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "").toLowerCase();
  } catch {
    return "";
  }
}

function isYoutube(url: string): boolean {
  const h = host(url);
  return h === "youtu.be" || h.endsWith("youtube.com");
}

function isGithub(url: string): boolean {
  return host(url) === "github.com";
}

export interface PartitionedResults {
  web: ResearchItem[];
  youtube: ResearchItem[];
  github: ResearchItem[];
  news: ResearchItem[];
  papers: ResearchItem[];
  total: number;
}

function githubRepoKey(url: string): string | null {
  try {
    const u = new URL(url);
    if (u.hostname.replace(/^www\./, "") !== "github.com") return null;
    const parts = u.pathname.split("/").filter(Boolean);
    if (parts.length < 2) return null;
    return `https://github.com/${parts[0]}/${parts[1]}`.toLowerCase();
  } catch {
    return null;
  }
}

function topicTokens(topic: string): string[] {
  const stop = new Set([
    "the", "and", "for", "are", "what", "how", "does", "from", "with", "that",
    "this", "have", "any", "there", "about", "best", "way", "tell", "give",
    "github", "youtube", "video", "videos", "tutorial", "repo", "repos",
  ]);
  return [...new Set(
    (topic.toLowerCase().match(/[a-z0-9]{3,}/g) ?? []).filter((w) => !stop.has(w)),
  )];
}

function githubRankScore(topic: string, item: ResearchItem): number {
  const tokens = topicTokens(topic);
  const slug = `${item.title} ${item.url}`.toLowerCase().replace(/[/\-_]/g, " ");
  let score = 0;
  if (tokens.length) {
    const inSlug = tokens.filter((t) => slug.includes(t));
    score += (inSlug.length / tokens.length) * 0.5;
    if (inSlug.length >= 2) score += 0.35;
    if (inSlug.length >= 3) score += 0.15;
  }
  if (/awesome|starred|my-awesome|365days|goodness|daily-ai/i.test(slug)) {
    score -= 0.45;
  }
  score += Math.min(Math.log1p(item.citation_count ?? 0) / 20, 0.1);
  return score;
}

function sortGithubByTopic(topic: string, items: ResearchItem[]): ResearchItem[] {
  return [...items].sort(
    (a, b) => githubRankScore(topic, b) - githubRankScore(topic, a),
  );
}

export function partitionResults(result: MultiSourceResearchResult): PartitionedResults {
  const web: ResearchItem[] = [];
  const youtube: ResearchItem[] = [];
  const githubFromWeb: ResearchItem[] = [];

  for (const item of result.tavily_results) {
    if (isYoutube(item.url)) {
      youtube.push(item);
    } else if (isGithub(item.url)) {
      githubFromWeb.push({ ...item, source: "github" });
    } else {
      web.push(item);
    }
  }

  const githubBest = new Map<string, ResearchItem>();
  for (const item of [...(result.github_results || []), ...githubFromWeb]) {
    const key = githubRepoKey(item.url) ?? item.url.toLowerCase();
    const prev = githubBest.get(key);
    const stars = item.citation_count ?? 0;
    const prevStars = prev?.citation_count ?? 0;
    if (!prev || stars > prevStars) {
      githubBest.set(key, item);
    }
  }
  const github = sortGithubByTopic(result.topic, Array.from(githubBest.values()));

  const news = result.news_results;
  const papers = result.papers_results;
  const total = web.length + youtube.length + github.length + news.length + papers.length;

  return { web, youtube, github, news, papers, total };
}

const TAB_ORDER: DisplayTab[] = ["web", "youtube", "github", "news", "papers"];

export function displayTabsForPartition(p: PartitionedResults, routed?: string[]): DisplayTab[] {
  const counts: Record<DisplayTab, number> = {
    web: p.web.length,
    youtube: p.youtube.length,
    github: p.github.length,
    news: p.news.length,
    papers: p.papers.length,
  };

  const routeSet = new Set(routed || []);
  const mapRoute: Record<DisplayTab, string> = {
    web: "tavily",
    youtube: "tavily",
    github: "github",
    news: "news",
    papers: "papers",
  };

  return TAB_ORDER.filter((tab) => {
    const n = counts[tab];
    if (n === 0) return false;
    if (routeSet.size && !routeSet.has(mapRoute[tab]) && tab !== "youtube" && tab !== "github") {
      return false;
    }
    if (tab === "youtube" || tab === "github") return n >= 1;
    return n > 1;
  });
}

export const DISPLAY_TAB_LABELS: Record<DisplayTab, string> = {
  web: "Web",
  youtube: "YouTube",
  github: "GitHub",
  news: "News",
  papers: "Papers",
};

export function itemsForTab(p: PartitionedResults, tab: DisplayTab): ResearchItem[] {
  return p[tab];
}
