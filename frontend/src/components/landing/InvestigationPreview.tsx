"use client";

export function InvestigationPreview() {
  const rows = [
    { id: "Q", label: "QUESTION", active: true },
    { id: "W", label: "WEB", active: true },
    { id: "P", label: "PAPERS", active: true },
    { id: "R", label: "REPOSITORY", active: true },
    { id: "E", label: "EVIDENCE", active: false },
    { id: "V", label: "VALIDATE", active: false },
    { id: "X", label: "REPORT", active: false },
  ];

  return (
    <div
      className="obs-panel relative h-full min-h-[22rem] overflow-hidden p-6 md:p-8"
      aria-hidden
    >
      <p className="obs-kicker mb-6">Live topology / preview</p>
      <div className="flex flex-col gap-0">
        {rows.map((row, i) => (
          <div key={row.id} className="flex items-stretch gap-3">
            <div className="flex w-8 flex-col items-center">
              <span
                className={row.active ? "obs-dot active" : "obs-dot"}
                style={{ marginTop: "0.35rem" }}
              />
              {i < rows.length - 1 && (
                <span
                  className="mt-1 w-px flex-1"
                  style={{ background: "var(--rule)", minHeight: "1.4rem" }}
                />
              )}
            </div>
            <div className="pb-3">
              <div className="obs-mono text-xs tracking-[0.16em] text-[var(--graphite)]">
                {String(i + 1).padStart(2, "0")}
              </div>
              <div
                className="text-sm tracking-[0.18em]"
                style={{
                  fontFamily: "var(--mono)",
                  color: row.active ? "var(--ink)" : "var(--muted)",
                }}
              >
                {row.label}
              </div>
            </div>
          </div>
        ))}
      </div>
      <div
        className="pointer-events-none absolute -right-8 -bottom-8 h-40 w-40 rounded-full opacity-40"
        style={{
          background:
            "radial-gradient(circle, rgba(232,93,4,0.18) 0%, transparent 70%)",
        }}
      />
    </div>
  );
}
