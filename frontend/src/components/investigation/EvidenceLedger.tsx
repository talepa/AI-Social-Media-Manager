"use client";

import type { LedgerEntry } from "@/lib/useInvestigationStream";

function fmt(ts: number) {
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function EvidenceLedger({ entries }: { entries: LedgerEntry[] }) {
  return (
    <aside
      className="flex max-h-[28rem] flex-col border-t md:max-h-none md:border-t-0 md:border-l"
      style={{ borderColor: "var(--rule)" }}
    >
      <div className="border-b px-4 py-3" style={{ borderColor: "var(--rule)" }}>
        <p className="obs-kicker">Evidence / Live</p>
      </div>
      <ul className="flex-1 overflow-y-auto p-4">
        {entries.length === 0 && (
          <li className="obs-mono text-[0.7rem] text-[var(--muted)]">Ledger empty</li>
        )}
        {entries.map((e) => (
          <li key={e.id} className="obs-slide-in mb-4 border-b pb-3" style={{ borderColor: "var(--rule)" }}>
            <div className="obs-mono text-[0.65rem] text-[var(--muted)]">{fmt(e.at)}</div>
            <div className="obs-mono text-xs tracking-[0.08em]">{e.label}</div>
            {e.meta && (
              <div className="mt-1 text-sm text-[var(--graphite)] line-clamp-2">{e.meta}</div>
            )}
          </li>
        ))}
      </ul>
    </aside>
  );
}
