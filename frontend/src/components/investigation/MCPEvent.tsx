"use client";

import type { McpLogEntry } from "@/lib/useInvestigationStream";

export function MCPEvent({ entries }: { entries: McpLogEntry[] }) {
  return (
    <div className="border-t p-4 md:p-5" style={{ borderColor: "var(--rule)" }}>
      <p className="obs-kicker mb-3">MCP Inspector</p>
      {entries.length === 0 ? (
        <p className="obs-mono text-[0.7rem] text-[var(--muted)]">
          Awaiting tool activity…
        </p>
      ) : (
        <ul className="flex max-h-48 flex-col gap-3 overflow-y-auto">
          {entries.map((e) => (
            <li key={e.id} className="obs-slide-in border-l-2 pl-3" style={{ borderColor: "var(--signal)" }}>
              <div className="obs-mono text-[0.65rem] tracking-[0.1em] text-[var(--muted)]">
                MCP / {e.server.toUpperCase()}
              </div>
              <div className="obs-mono text-sm">{e.tool}</div>
              <div className="text-xs text-[var(--graphite)]">{e.detail}</div>
              <div className="obs-mono mt-1 text-[0.6rem] text-[var(--success)]">
                {e.status.toUpperCase()}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
