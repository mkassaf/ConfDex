const BASE = "/api/ollama";

export interface OllamaStatus {
  running: boolean;
  host: string;
}

export async function getOllamaStatus(): Promise<OllamaStatus> {
  const r = await fetch(`${BASE}/status`);
  if (!r.ok) return { running: false, host: "" };
  return r.json();
}

export async function getOllamaModels(): Promise<string[]> {
  const r = await fetch(`${BASE}/models`);
  if (!r.ok) return [];
  const data = await r.json();
  return data.models ?? [];
}

export function pullModelStream(
  model: string,
  onProgress: (msg: string, pct: number | null) => void,
  onDone: () => void,
  onError: (e: string) => void,
): () => void {
  const controller = new AbortController();

  fetch(`${BASE}/pull`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model }),
    signal: controller.signal,
  }).then(async (resp) => {
    const reader = resp.body?.getReader();
    if (!reader) { onDone(); return; }
    const decoder = new TextDecoder();
    let buf = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop() ?? "";
      for (const line of lines) {
        const text = line.replace(/^data:\s*/, "").trim();
        if (!text) continue;
        try {
          const obj = JSON.parse(text);
          if (obj.status === "done") { onDone(); return; }
          const pct = obj.total && obj.completed
            ? Math.round((obj.completed / obj.total) * 100)
            : null;
          onProgress(obj.status ?? "", pct);
        } catch { /* skip */ }
      }
    }
    onDone();
  }).catch((e) => {
    if (e.name !== "AbortError") onError(String(e));
  });

  return () => controller.abort();
}
