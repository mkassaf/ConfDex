import { useState } from "react";
import { pullModelStream } from "../api/ollama";

interface Props {
  onInstalled: () => void;
}

export function OllamaInstaller({ onInstalled }: Props) {
  const [modelInput, setModelInput] = useState("llama3.2");
  const [pulling, setPulling] = useState(false);
  const [progress, setProgress] = useState<string>("");
  const [pct, setPct] = useState<number | null>(null);
  const [error, setError] = useState<string>("");

  function handlePull() {
    if (!modelInput.trim()) return;
    setPulling(true);
    setError("");
    setProgress("Starting…");
    const cancel = pullModelStream(
      modelInput.trim(),
      (msg, p) => { setProgress(msg); if (p !== null) setPct(p); },
      () => { setPulling(false); setPct(null); setProgress(""); onInstalled(); },
      (e) => { setPulling(false); setError(e); },
    );
    return cancel;
  }

  return (
    <div className="mt-2 p-3 bg-gray-800 rounded-lg border border-gray-700 space-y-2">
      <p className="text-sm font-medium text-gray-300">Install Ollama model</p>
      <div className="flex gap-2">
        <input
          className="flex-1 px-3 py-1.5 bg-gray-900 border border-gray-600 rounded text-sm text-white
                     focus:outline-none focus:ring-1 focus:ring-blue-500"
          value={modelInput}
          onChange={(e) => setModelInput(e.target.value)}
          placeholder="e.g. llama3.2, qwen2.5:7b"
          disabled={pulling}
        />
        <button
          onClick={handlePull}
          disabled={pulling || !modelInput.trim()}
          className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white
                     text-sm rounded font-medium transition-colors"
        >
          {pulling ? "Pulling…" : "Install"}
        </button>
      </div>
      {pulling && (
        <div className="space-y-1">
          <div className="w-full bg-gray-700 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full transition-all"
              style={{ width: pct !== null ? `${pct}%` : "20%", animation: pct === null ? "pulse 1.5s infinite" : undefined }}
            />
          </div>
          <p className="text-xs text-gray-400">{progress}{pct !== null ? ` (${pct}%)` : ""}</p>
        </div>
      )}
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
}
