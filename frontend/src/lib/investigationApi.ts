import type { DirectorRequest, InvestigationRunResponse } from "./investigationTypes";

const API_BASE =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) ||
  "http://localhost:8001";

export function apiUrl(path: string): string {
  if (path.startsWith("http")) return path;
  return `${API_BASE.replace(/\/$/, "")}${path.startsWith("/") ? path : `/${path}`}`;
}

export async function fetchMcpCapabilities(): Promise<unknown> {
  const res = await fetch(apiUrl("/api/mcp/capabilities"));
  if (!res.ok) throw new Error(`MCP capabilities failed: ${res.status}`);
  return res.json();
}

export async function fetchRun(runId: string) {
  const res = await fetch(apiUrl(`/api/investigation/runs/${runId}`));
  if (!res.ok) throw new Error(`Run fetch failed: ${res.status}`);
  return res.json();
}

/** Parse SSE stream from POST /api/investigation/runs/stream */
export async function* streamInvestigation(
  body: DirectorRequest,
  signal?: AbortSignal,
): AsyncGenerator<{ event: string; data: unknown }> {
  const res = await fetch(apiUrl("/api/investigation/runs/stream"), {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`Stream failed: ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() || "";

    for (const chunk of chunks) {
      const lines = chunk.split("\n");
      let event = "message";
      const dataLines: string[] = [];
      for (const line of lines) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
      }
      if (!dataLines.length) continue;
      const raw = dataLines.join("\n");
      let data: unknown = raw;
      try {
        data = JSON.parse(raw);
      } catch {
        /* keep string */
      }
      yield { event, data };
    }
  }
}

export type { InvestigationRunResponse };
