import type { DisplayTab } from "./partitionResults";

export interface ThumbItem {
  title: string;
  url: string;
  image_url?: string | null;
  favicon_url?: string | null;
  venue?: string | null;
}

export type ThumbKind = "github" | "youtube" | "paper" | "news" | "web";

export interface ThumbDisplay {
  kind: ThumbKind;
  heroUrl: string | null;
  faviconUrl: string | null;
  label: string;
}

function host(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "").toLowerCase();
  } catch {
    return "";
  }
}

function youtubeId(url: string): string | null {
  try {
    const u = new URL(url);
    if (u.hostname.includes("youtu.be")) {
      const id = u.pathname.slice(1).split("/")[0];
      return id?.length === 11 ? id : null;
    }
    if (u.hostname.includes("youtube.com")) {
      const v = u.searchParams.get("v");
      if (v && v.length === 11) return v;
      const m = u.pathname.match(/\/(?:embed|shorts|v)\/([\w-]{11})/);
      if (m) return m[1];
    }
  } catch {
    /* ignore */
  }
  return null;
}

function imageMatchesPage(imageUrl: string, pageUrl: string): boolean {
  try {
    const imgHost = host(imageUrl);
    const pageHost = host(pageUrl);
    if (!imgHost || !pageHost) return false;
    if (imgHost === pageHost) return true;
    return imgHost.endsWith(`.${pageHost}`) || pageHost.endsWith(`.${imgHost}`);
  } catch {
    return false;
  }
}

function isSmallIcon(url: string): boolean {
  const u = url.toLowerCase();
  return (
    u.includes("favicon") ||
    u.includes("s2/favicons") ||
    u.includes("google.com/s2/favicons") ||
    u.endsWith(".ico")
  );
}

function isGithubAvatar(url: string): boolean {
  return /avatars\.githubusercontent\.com/i.test(url);
}

function faviconFor(url: string): string {
  const h = host(url);
  if (!h) return "";
  return `https://www.google.com/s2/favicons?domain=${encodeURIComponent(h)}&sz=128`;
}

export function resolveThumbDisplay(
  tab: DisplayTab,
  item: ThumbItem,
): ThumbDisplay {
  const h = host(item.url);
  const kind: ThumbKind =
    tab === "github" || h === "github.com"
      ? "github"
      : tab === "youtube" || h.includes("youtube.com") || h === "youtu.be"
        ? "youtube"
        : tab === "papers"
          ? "paper"
          : tab === "news"
            ? "news"
            : "web";

  const favicon = item.favicon_url || faviconFor(item.url);

  if (kind === "github") {
    const avatar =
      (item.image_url && isGithubAvatar(item.image_url) ? item.image_url : null) ||
      null;
    return {
      kind,
      heroUrl: avatar,
      faviconUrl: favicon,
      label: item.title.split("/")[0] || "GitHub",
    };
  }

  if (kind === "youtube") {
    const id = youtubeId(item.url);
    const thumb = id ? `https://img.youtube.com/vi/${id}/hqdefault.jpg` : null;
    return {
      kind,
      heroUrl: thumb,
      faviconUrl: favicon,
      label: "YouTube",
    };
  }

  if (kind === "paper") {
    return {
      kind,
      heroUrl: null,
      faviconUrl: favicon,
      label: item.venue?.split("·")[0]?.trim() || "Paper",
    };
  }

  const heroCandidate = item.image_url?.trim() || "";
  const useHero =
    !!heroCandidate &&
    !isSmallIcon(heroCandidate) &&
    !isGithubAvatar(heroCandidate) &&
    imageMatchesPage(heroCandidate, item.url);

  return {
    kind,
    heroUrl: useHero ? heroCandidate : null,
    faviconUrl: favicon,
    label: h || kind,
  };
}
