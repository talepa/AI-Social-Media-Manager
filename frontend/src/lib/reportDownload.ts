/**
 * Client-side report download helpers (MD / JSON / printable HTML→PDF).
 */

const API_BASE = "http://localhost:8001";

export type DownloadableReport = Record<string, unknown>;

function slugify(topic: string): string {
  return (
    topic
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, 48) || "research"
  );
}

function triggerBlobDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export async function downloadReportMarkdown(report: DownloadableReport, topic: string) {
  const res = await fetch(`${API_BASE}/api/research/export/markdown`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ report }),
  });
  if (!res.ok) throw new Error("Markdown export failed");
  const text = await res.text();
  triggerBlobDownload(
    new Blob([text], { type: "text/markdown;charset=utf-8" }),
    `${slugify(topic)}-report.md`,
  );
}

export async function downloadReportJson(report: DownloadableReport, topic: string) {
  const res = await fetch(`${API_BASE}/api/research/export/json`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ report }),
  });
  if (!res.ok) throw new Error("JSON export failed");
  const text = await res.text();
  triggerBlobDownload(
    new Blob([text], { type: "application/json;charset=utf-8" }),
    `${slugify(topic)}-report.json`,
  );
}

/** Opens printable HTML; user can Save as PDF from the print dialog. */
export async function openReportPrintPdf(report: DownloadableReport) {
  const res = await fetch(`${API_BASE}/api/research/export/html`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ report }),
  });
  if (!res.ok) throw new Error("HTML export failed");
  const html = await res.text();
  const w = window.open("", "_blank");
  if (!w) throw new Error("Pop-up blocked — allow pop-ups to print / save PDF");
  w.document.open();
  w.document.write(html);
  w.document.close();
  // Give images a moment, then print
  w.focus();
  window.setTimeout(() => {
    try {
      w.print();
    } catch {
      /* user can print manually */
    }
  }, 400);
}
