"use client";

import type { AgentStationId, StationStatus } from "@/lib/investigationTypes";

const LABELS: Record<AgentStationId, string> = {
  director: "Director",
  web: "Web",
  academic: "Academic",
  repository: "Repository",
  evidence: "Evidence",
  synthesis: "Report",
};

const STATUS_COPY: Record<StationStatus, string> = {
  waiting: "waiting",
  active: "active",
  done: "complete",
  error: "error",
};

export function AgentRail({
  stations,
}: {
  stations: Record<AgentStationId, StationStatus>;
}) {
  const order: AgentStationId[] = [
    "director",
    "web",
    "academic",
    "repository",
    "evidence",
    "synthesis",
  ];

  return (
    <aside className="flex flex-row gap-4 overflow-x-auto border-b p-4 md:flex-col md:gap-0 md:overflow-visible md:border-b-0 md:border-r md:p-5" style={{ borderColor: "var(--rule)" }}>
      <p className="obs-kicker mb-3 hidden md:block">Agents</p>
      {order.map((id, i) => {
        const st = stations[id];
        return (
          <div key={id} className="flex min-w-[7.5rem] items-start gap-3 py-2 md:min-w-0">
            <div className="flex flex-col items-center pt-1">
              <span
                className={
                  st === "active"
                    ? "obs-pulse"
                    : st === "done"
                      ? "obs-dot done"
                      : "obs-dot"
                }
              />
              {i < order.length - 1 && (
                <span
                  className="mt-1 hidden w-px flex-1 md:block"
                  style={{ background: "var(--rule)", minHeight: "1.25rem" }}
                />
              )}
            </div>
            <div>
              <div className="obs-mono text-[0.65rem] tracking-[0.14em] text-[var(--muted)]">
                {String(i + 1).padStart(2, "0")}
              </div>
              <div className="text-sm tracking-wide">{LABELS[id]}</div>
              <div
                className="obs-mono text-[0.65rem]"
                style={{
                  color: st === "active" ? "var(--signal)" : "var(--muted)",
                }}
              >
                {STATUS_COPY[st]}
              </div>
            </div>
          </div>
        );
      })}
    </aside>
  );
}
