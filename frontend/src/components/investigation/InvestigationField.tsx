"use client";

import type { AgentStationId, StationStatus } from "@/lib/investigationTypes";

export function InvestigationField({
  stations,
  phase,
  packetActive,
}: {
  stations: Record<AgentStationId, StationStatus>;
  phase: string;
  packetActive: boolean;
}) {
  const node = (id: AgentStationId, label: string, mcp?: string) => {
    const st = stations[id];
    return (
      <div className="flex flex-col items-center gap-1">
        <div
          className="obs-panel px-3 py-2 text-center"
          style={{
            borderColor:
              st === "active"
                ? "var(--signal)"
                : st === "done"
                  ? "var(--success)"
                  : "var(--rule)",
            minWidth: "6.5rem",
          }}
        >
          <div className="obs-mono text-[0.6rem] tracking-[0.12em] text-[var(--muted)]">
            {label}
          </div>
          {mcp && (
            <div className="obs-mono mt-1 text-[0.55rem] text-[var(--graphite)]">
              {mcp}
            </div>
          )}
        </div>
        {st === "active" && <span className="obs-pulse" />}
      </div>
    );
  };

  return (
    <div className="relative flex min-h-[18rem] flex-col items-center justify-center gap-4 p-4 md:p-8">
      <p className="obs-kicker absolute top-4 left-4">Investigation field</p>
      <p className="obs-mono absolute top-4 right-4 text-[0.65rem] text-[var(--muted)]">
        phase · {phase}
      </p>

      {node("director", "01 DIRECTOR")}

      <div className="relative h-8 w-px" style={{ background: "var(--rule)" }}>
        {packetActive && (
          <span
            className="absolute left-1/2 h-1.5 w-1.5 -translate-x-1/2 rounded-full bg-[var(--signal)]"
            style={{ animation: "obs-slide-in 0.8s ease-in-out infinite alternate" }}
          />
        )}
      </div>

      <div className="flex flex-wrap items-start justify-center gap-6 md:gap-10">
        {node("web", "WEB", "MCP-01")}
        {node("academic", "ACADEMIC", "MCP-02")}
        {node("repository", "REPOSITORY", "MCP-03")}
      </div>

      <div className="h-8 w-px" style={{ background: "var(--rule)" }} />
      {node("evidence", "EVIDENCE")}
      <div className="h-8 w-px" style={{ background: "var(--rule)" }} />
      {node("synthesis", "REPORT")}
    </div>
  );
}
