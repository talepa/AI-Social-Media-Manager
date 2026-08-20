export async function shareQuestion(question: string): Promise<"shared" | "copied"> {
  const url =
    typeof window !== "undefined"
      ? `${window.location.origin}${window.location.pathname}?q=${encodeURIComponent(question)}`
      : "";
  const text = `Research on Atelier:\n\n“${question}”`;

  if (typeof navigator !== "undefined" && navigator.share) {
    try {
      await navigator.share({
        title: "Atelier Research",
        text,
        url,
      });
      return "shared";
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") {
        throw e;
      }
    }
  }

  await navigator.clipboard.writeText(`${text}\n\n${url}`);
  return "copied";
}

export async function copyText(text: string): Promise<void> {
  await navigator.clipboard.writeText(text);
}
