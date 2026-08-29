"use client";

import { useCallback, useRef, useState } from "react";
import { streamInvestigation } from "./investigationApi";
import type {
  AgentStationId,
  DirectorRequest,
  InvestigationRunResponse,
  NodeEvent,
  ProgressEvent,
  RunPhase,
  StationStatus,
} from "./investigationTypes";

export interface McpLogEntry {
  id: string;
  at: number;
  server: string;
  tool: string;
  detail: string;
  status: "active" | "complete";
}

export interface LedgerEntry {
  id: string;
  at: number;
  label: string;
  kind: string;
  meta?: string;
}

const STATIONS: AgentStationId[] = [
  "director",
  "web",
  "academic",
  "repository",
  "evidence",
  "synthesis",
];

function emptyStations(): Record<AgentStationId, StationStatus> {
  return {
    director: "waiting",
    web: "waiting",
    academic: "waiting",
    repository: "waiting",
    evidence: "waiting",
    synthesis: "waiting",
  };
}

function phaseFromEventType(et: string): RunPhase | null {
  if (et === "run_started" || et === "plan_created") return "director";
  if (et.startsWith("specialist")) return "specialists";
  if (et.startsWith("evidence")) return "evidence";
  if (et.startsWith("synthesis") || et === "citation_validated") return "synthesis";
  return null;
}

function applyPhase(
  stations: Record<AgentStationId, StationStatus>,
  phase: RunPhase,
  required: string[] = [],
): Record<AgentStationId, StationStatus> {
  const next = { ...stations };
  const markDone = (ids: AgentStationId[]) => {
    for (const id of ids) {
      if (next[id] !== "error") next[id] = "done";
    }
  };
  const markActive = (id: AgentStationId) => {
    if (next[id] !== "done" && next[id] !== "error") next[id] = "active";
  };

  if (phase === "director") {
    markActive("director");
  } else if (phase === "specialists") {
    markDone(["director"]);
    const specs = (required.length ? required : ["web", "academic", "repository"]) as AgentStationId[];
    for (const s of specs) {
      if (s === "web" || s === "academic" || s === "repository") markActive(s);
    }
  } else if (phase === "evidence") {
    markDone(["director", "web", "academic", "repository"]);
    markActive("evidence");
  } else if (phase === "synthesis") {
    markDone(["director", "web", "academic", "repository", "evidence"]);
    markActive("synthesis");
  } else if (phase === "complete") {
    for (const id of STATIONS) next[id] = "done";
  }
  return next;
}

export function useInvestigationStream() {
  const [phase, setPhase] = useState<RunPhase>("idle");
  const [runId, setRunId] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [stations, setStations] = useState(emptyStations);
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [mcpLog, setMcpLog] = useState<McpLogEntry[]>([]);
  const [ledger, setLedger] = useState<LedgerEntry[]>([]);
  const [node, setNode] = useState<NodeEvent | null>(null);
  const [result, setResult] = useState<InvestigationRunResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const requiredRef = useRef<string[]>([]);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setPhase("idle");
    setRunId(null);
    setQuestion("");
    setStations(emptyStations());
    setEvents([]);
    setMcpLog([]);
    setLedger([]);
    setNode(null);
    setResult(null);
    setError(null);
    setRunning(false);
    requiredRef.current = [];
  }, []);

  const start = useCallback(async (body: DirectorRequest) => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    setRunning(true);
    setError(null);
    setResult(null);
    setEvents([]);
    setMcpLog([]);
    setLedger([]);
    setNode(null);
    setStations(emptyStations());
    setPhase("accepted");
    setQuestion(body.question);
    requiredRef.current = [];

    const pushLedger = (entry: Omit<LedgerEntry, "at">) => {
      setLedger((prev) => [{ ...entry, at: Date.now() }, ...prev].slice(0, 80));
    };
    const pushMcp = (entry: Omit<McpLogEntry, "at" | "id">) => {
      setMcpLog((prev) =>
        [{ ...entry, id: `${Date.now()}-${prev.length}`, at: Date.now() }, ...prev].slice(
          0,
          40,
        ),
      );
    };

    try {
      for await (const { event, data } of streamInvestigation(body, ac.signal)) {
        if (event === "accepted") {
          const d = data as { run_id: string; question?: string };
          setRunId(d.run_id);
          setPhase("accepted");
          pushLedger({
            id: `acc-${d.run_id}`,
            label: "RUN ACCEPTED",
            kind: "system",
            meta: d.run_id.slice(0, 8),
          });
        } else if (event === "progress") {
          const ev = data as ProgressEvent;
          setEvents((prev) => [...prev, ev]);
          const et = String(ev.event_type || "");
          const mapped = phaseFromEventType(et);
          if (mapped) {
            setPhase(mapped);
            if (et === "plan_created" && Array.isArray(ev.required_specialists)) {
              requiredRef.current = ev.required_specialists as string[];
            }
            setStations((s) => applyPhase(s, mapped, requiredRef.current));
          }

          if (et === "plan_created") {
            pushLedger({
              id: `plan-${Date.now()}`,
              label: "PLAN",
              kind: "director",
              meta: String(ev.objective || "Director plan ready"),
            });
            pushMcp({
              server: "director",
              tool: "create_research_plan",
              detail: String(ev.objective || "plan"),
              status: "complete",
            });
          } else if (et === "specialists_completed") {
            const count = Number(ev.source_count ?? ev.finding_count ?? 0);
            pushLedger({
              id: `spec-${Date.now()}`,
              label: "SPECIALISTS",
              kind: "agents",
              meta: `${count} signals`,
            });
            pushMcp({
              server: "research|academic|repository",
              tool: "specialist_fanout",
              detail: `sources/findings updated`,
              status: "complete",
            });
          } else if (et.startsWith("evidence")) {
            pushLedger({
              id: `ev-${Date.now()}`,
              label: "EVIDENCE",
              kind: "evidence",
              meta: et.replace(/_/g, " "),
            });
            pushMcp({
              server: "evidence",
              tool: "analyze_evidence",
              detail: et,
              status: "complete",
            });
          } else if (et === "citation_validated") {
            pushLedger({
              id: `cite-${Date.now()}`,
              label: "VALIDATION",
              kind: "validation",
              meta: ev.passed ? "PASS" : "FAIL",
            });
          } else if (et.startsWith("synthesis")) {
            pushLedger({
              id: `syn-${Date.now()}`,
              label: "REPORT",
              kind: "synthesis",
              meta: et.replace(/_/g, " "),
            });
          }
        } else if (event === "node") {
          const n = data as NodeEvent;
          setNode(n);
          const p = (n.phase || "") as string;
          if (p.includes("director") || p === "initialize") {
            setPhase("director");
            setStations((s) => applyPhase(s, "director"));
          } else if (p.includes("specialist")) {
            setPhase("specialists");
            setStations((s) => applyPhase(s, "specialists", requiredRef.current));
          } else if (p.includes("evidence")) {
            setPhase("evidence");
            setStations((s) => applyPhase(s, "evidence"));
          } else if (p.includes("synthesis") || p.includes("report")) {
            setPhase("synthesis");
            setStations((s) => applyPhase(s, "synthesis"));
          }
        } else if (event === "complete") {
          const r = data as InvestigationRunResponse;
          setResult(r);
          setPhase("complete");
          setStations((s) => applyPhase(s, "complete"));
          requiredRef.current = r.plan?.required_specialists || [];
          pushLedger({
            id: `done-${r.run_id}`,
            label: "COMPLETE",
            kind: "system",
            meta: `${r.sources?.length ?? 0} sources · ${r.evidence?.claims?.length ?? 0} claims`,
          });
        } else if (event === "error") {
          const d = data as { error?: string; run_id?: string };
          setError(d.error || "Investigation failed");
          setPhase("error");
        }
      }
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setError((err as Error).message || "Stream failed");
      setPhase("error");
    } finally {
      setRunning(false);
    }
  }, []);

  return {
    phase,
    runId,
    question,
    stations,
    events,
    mcpLog,
    ledger,
    node,
    result,
    error,
    running,
    start,
    reset,
  };
}
