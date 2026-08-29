"use client";

import { useMemo, useState } from "react";
import type {
  EvidenceClaim,
  InvestigationRunResponse,
  SourceRecord,
} from "@/lib/investigationTypes";
import { SourceInspector } from "./SourceInspector";

export function EvidenceWorkspace({
  result,
}: {
  result: InvestigationRunResponse;
}) {
  const claims = useMemo(() => result.evidence?.claims ?? [], [result.evidence]);
  const sources = useMemo(() => result.sources ?? [], [result.sources]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [sourceId, setSourceId] = useState<string | null>(null);

  const effectiveSelectedId = selectedId ?? claims[0]?.id ?? null;

  const selected: EvidenceClaim | null = useMemo(
    () => claims.find((c) => c.id === effectiveSelectedId) ?? null,
    [claims, effectiveSelectedId],
  );

  const sourceMap = useMemo(() => {
    const m = new Map<string, SourceRecord>();
    for (const s of sources) m.set(s.id, s);
    return m;
  }, [sources]);

  const activeSource = sourceId ? sourceMap.get(sourceId) ?? null : null;

  return (
    <div className="grid gap-0 border-t lg:grid-cols-[14rem_1fr_16rem]" style={{ borderColor: "var(--rule)" }}>
      <div className="border-b lg:border-b-0 lg:border-r" style={{ borderColor: "var(--rule)" }}>
        <div className="border-b px-4 py-3" style={{ borderColor: "var(--rule)" }}>
          <p className="obs-kicker">Claims</p>
        </div>
        <ul className="max-h-72 overflow-y-auto lg:max-h-[28rem]">
          {claims.map((c, i) => (
            <li key={c.id}>
              <button
                type="button"
                onClick={() => setSelectedId(c.id)}
                className="w-full border-b px-4 py-3 text-left"
                style={{
                  borderColor: "var(--rule)",
                  background: effectiveSelectedId === c.id ? "var(--signal-soft)" : "transparent",
                }}
              >
                <div className="obs-mono text-[0.65rem] text-[var(--muted)]">
                  {String(i + 1).padStart(2, "0")} · {c.id}
                </div>
                <div className="mt-1 line-clamp-2 text-sm">{c.claim}</div>
              </button>
            </li>
          ))}
          {claims.length === 0 && (
            <li className="px-4 py-6 obs-mono text-[0.7rem] text-[var(--muted)]">
              No claims yet
            </li>
          )}
        </ul>
      </div>

      <div className="p-5 md:p-6">
        {selected ? (
          <>
            <p className="obs-kicker">Selected claim</p>
            <h2 className="obs-display mt-2 text-2xl">{selected.claim}</h2>
            <div className="obs-mono mt-4 flex flex-wrap gap-4 text-[0.65rem] text-[var(--muted)]">
              <span>CONFIDENCE {selected.confidence.toFixed(2)}</span>
              <span>STRENGTH {selected.strength}</span>
              <span>AGREEMENT {selected.agreement_count}</span>
            </div>

            <hr className="obs-rule my-5" />

            <p className="obs-kicker mb-2">Support</p>
            <div className="mb-4 flex flex-wrap gap-2">
              {selected.supporting_source_ids.map((id) => (
                <button
                  key={id}
                  type="button"
                  className="cite-chip"
                  onClick={() => setSourceId(id)}
                >
                  {id}
                </button>
              ))}
              {selected.supporting_source_ids.length === 0 && (
                <span className="obs-mono text-[0.7rem] text-[var(--muted)]">None</span>
              )}
            </div>

            <p className="obs-kicker mb-2">Contradiction</p>
            <div className="mb-4 flex flex-wrap gap-2">
              {selected.contradicting_source_ids.map((id) => (
                <button
                  key={id}
                  type="button"
                  className="cite-chip"
                  onClick={() => setSourceId(id)}
                >
                  {id}
                </button>
              ))}
              {selected.contradicting_source_ids.length === 0 && (
                <span className="obs-mono text-[0.7rem] text-[var(--muted)]">None</span>
              )}
            </div>

            {selected.uncertainty_notes && (
              <>
                <p className="obs-kicker mb-2">Uncertainty</p>
                <p className="text-sm text-[var(--graphite)]">{selected.uncertainty_notes}</p>
              </>
            )}
          </>
        ) : (
          <p className="obs-mono text-[0.7rem] text-[var(--muted)]">Select a claim</p>
        )}
      </div>

      <SourceInspector
        source={activeSource}
        usedBy={
          activeSource
            ? claims
                .filter(
                  (c) =>
                    c.supporting_source_ids.includes(activeSource.id) ||
                    c.contradicting_source_ids.includes(activeSource.id),
                )
                .map((c) => c.id)
            : []
        }
        onClose={() => setSourceId(null)}
      />
    </div>
  );
}
