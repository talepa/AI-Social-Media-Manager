"use client";

import type { SourceRecord } from "@/lib/investigationTypes";

export function SourceInspector({
  source,
  usedBy,
  onClose,
}: {
  source: SourceRecord | null;
  usedBy: string[];
  onClose: () => void;
}) {
  return (
    <div
      className="border-t p-4 lg:border-t-0 lg:border-l"
      style={{ borderColor: "var(--rule)", background: "var(--surface)" }}
    >
      <div className="mb-3 flex items-center justify-between">
        <p className="obs-kicker">Source inspector</p>
        {source && (
          <button type="button" className="obs-mono text-[0.65rem] text-[var(--muted)]" onClick={onClose}>
            Clear
          </button>
        )}
      </div>
      {!source ? (
        <p className="obs-mono text-[0.7rem] text-[var(--muted)]">
          Select a source id from a claim
        </p>
      ) : (
        <div className="space-y-3 text-sm">
          <div className="obs-mono text-xs tracking-[0.1em]">{source.id}</div>
          <h3 className="obs-display text-lg leading-snug">{source.title}</h3>
          <div className="obs-mono text-[0.65rem] text-[var(--muted)]">
            {source.type.toUpperCase()} · {source.specialist}
          </div>
          {source.url && (
            <a
              href={source.url}
              target="_blank"
              rel="noreferrer"
              className="obs-mono block break-all text-[0.65rem] text-[var(--signal)]"
            >
              {source.url}
            </a>
          )}
          <p className="text-[var(--graphite)] leading-relaxed">
            {(source.content || "").slice(0, 420) || "No snippet"}
          </p>
          <hr className="obs-rule" />
          <p className="obs-kicker">Used by</p>
          <div className="flex flex-wrap gap-2">
            {usedBy.map((id) => (
              <span key={id} className="cite-chip">
                {id}
              </span>
            ))}
            {usedBy.length === 0 && (
              <span className="obs-mono text-[0.65rem] text-[var(--muted)]">—</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
