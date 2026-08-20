"use client";

import type { ThumbDisplay } from "../lib/sourceThumb";

function GitHubMark() {
  return (
    <svg viewBox="0 0 98 96" aria-hidden className="brand-mark-svg">
      <path
        fill="currentColor"
        d="M48.854 0C21.839 0 0 22 0 49.217c0 21.756 13.993 40.172 33.405 46.69 2.427.49 3.316-1.059 3.316-2.362 0-1.141-.08-5.052-.08-9.127-13.59 2.934-16.42-5.867-16.42-5.867-2.184-5.704-5.42-7.22-5.42-7.22-4.362-2.988.344-2.988.344-2.988 4.954.34 7.525 5.094 7.525 5.094 4.367 7.496 11.404 5.378 14.235 4.074.404-3.255 1.649-5.378 3.019-6.613-10.839-1.141-22.243-5.378-22.243-24.283 0-5.378 1.94-9.778 5.094-13.2-.52-1.25-2.188-6.32.49-13.138 0 0 4.125-1.304 13.426 5.052a46.97 46.97 0 0 1 12.214-1.63c4.125 0 8.33.571 12.213 1.63 9.302-6.356 13.427-5.052 13.427-5.052 2.679 6.818 1.01 11.888.49 13.138 3.155 3.522 5.094 7.822 5.094 13.2 0 18.905-11.404 23.06-22.324 24.283 1.78 1.548 3.316 4.481 3.316 9.126 0 6.613-.08 11.888-.08 13.447 0 1.304 1.005 2.853 3.316 2.364 19.412-6.52 33.405-24.935 33.405-46.691C97.707 22 75.788 0 48.854 0Z"
      />
    </svg>
  );
}

function YouTubeMark() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden className="brand-mark-svg">
      <path
        fill="currentColor"
        d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.5 12 3.5 12 3.5s-7.5 0-9.4.6A3 3 0 0 0 .5 6.2 31 31 0 0 0 0 12a31 31 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.9.6 9.4.6 9.4.6s7.5 0 9.4-.6a3 3 0 0 0 2.1-2.1A31 31 0 0 0 24 12a31 31 0 0 0-.5-5.8ZM9.75 15.02V8.98L15.5 12l-5.75 3.02Z"
      />
    </svg>
  );
}

function PaperMark() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden className="brand-mark-svg">
      <path
        fill="currentColor"
        d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6Zm-1 2 5 5h-5V4ZM8 12h8v2H8v-2Zm0 4h8v2H8v-2Z"
      />
    </svg>
  );
}

export default function SourceThumb({ display }: { display: ThumbDisplay }) {
  const { kind, heroUrl, faviconUrl } = display;

  if (kind === "youtube" && heroUrl) {
    return (
      <div className={`source-thumb source-thumb--${kind}`}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={heroUrl} alt="" className="source-thumb-hero" referrerPolicy="no-referrer" />
        <span className="source-thumb-play" aria-hidden>
          ▶
        </span>
      </div>
    );
  }

  if (kind === "web" && heroUrl) {
    return (
      <div className={`source-thumb source-thumb--${kind}`}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={heroUrl} alt="" className="source-thumb-hero" referrerPolicy="no-referrer" />
        {faviconUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={faviconUrl} alt="" className="source-thumb-badge" referrerPolicy="no-referrer" />
        ) : null}
      </div>
    );
  }

  if (kind === "github") {
    return (
      <div className={`source-thumb source-thumb--${kind}`}>
        <GitHubMark />
        {heroUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={heroUrl} alt="" className="source-thumb-avatar" referrerPolicy="no-referrer" />
        ) : null}
      </div>
    );
  }

  if (kind === "youtube") {
    return (
      <div className={`source-thumb source-thumb--${kind}`}>
        <YouTubeMark />
      </div>
    );
  }

  if (kind === "paper") {
    return (
      <div className={`source-thumb source-thumb--${kind}`}>
        <PaperMark />
        {faviconUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={faviconUrl} alt="" className="source-thumb-badge" referrerPolicy="no-referrer" />
        ) : null}
      </div>
    );
  }

  return (
    <div className={`source-thumb source-thumb--${kind}`}>
      {faviconUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={faviconUrl} alt="" className="source-thumb-favicon-lg" referrerPolicy="no-referrer" />
      ) : (
        <PaperMark />
      )}
    </div>
  );
}
