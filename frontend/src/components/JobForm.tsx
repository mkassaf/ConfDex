import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createJob } from "../api/jobs";
import { LLMSelector, type LLMConfig } from "./LLMSelector";

export function JobForm() {
  const qc = useQueryClient();
  const [inputMode, setInputMode] = useState<"conference" | "urls">("conference");
  const [conference, setConference] = useState("");
  const [urlsText, setUrlsText] = useState("");
  const [topic, setTopic] = useState("");
  const [llmConfig, setLlmConfig] = useState<LLMConfig>({
    source: "remote",
    model: "claude-sonnet-4-6",
    api_key: "",
  });
  const [useLLMFallback, setUseLLMFallback] = useState(false);
  const [error, setError] = useState("");

  const { mutate, isPending } = useMutation({
    mutationFn: createJob,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
      setError("");
    },
    onError: (e: Error) => setError(e.message),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    const track_urls =
      inputMode === "urls"
        ? urlsText.split("\n").map((u) => u.trim()).filter(Boolean)
        : undefined;

    mutate({
      conference: inputMode === "conference" ? conference.trim() || undefined : undefined,
      track_urls,
      topic: topic.trim() || undefined,
      model: llmConfig.model,
      api_key: llmConfig.api_key || undefined,
      use_llm_fallback: useLLMFallback,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <div className="flex gap-2 mb-3">
          {(["conference", "urls"] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setInputMode(m)}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors border ${
                inputMode === m
                  ? "bg-indigo-600 border-indigo-500 text-white"
                  : "bg-gray-800 border-gray-700 text-gray-400 hover:text-white"
              }`}
            >
              {m === "conference" ? "Conference slug" : "Custom URLs"}
            </button>
          ))}
        </div>

        {inputMode === "conference" ? (
          <div>
            <label className="block text-xs text-gray-400 mb-1">Conference slug</label>
            <input
              type="text"
              value={conference}
              onChange={(e) => setConference(e.target.value)}
              placeholder="e.g. icse-2026, fse-2025"
              required
              className="w-full px-3 py-2 bg-gray-900 border border-gray-600 rounded text-sm text-white
                         focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
        ) : (
          <div>
            <label className="block text-xs text-gray-400 mb-1">Track URLs (one per line)</label>
            <textarea
              value={urlsText}
              onChange={(e) => setUrlsText(e.target.value)}
              rows={4}
              required
              placeholder={"https://conf.researchr.org/track/icse-2026/icse-2026-research-track\nhttps://..."}
              className="w-full px-3 py-2 bg-gray-900 border border-gray-600 rounded text-sm text-white
                         focus:outline-none focus:ring-1 focus:ring-indigo-500 resize-none font-mono"
            />
          </div>
        )}
      </div>

      <div>
        <label className="block text-xs text-gray-400 mb-1">
          Topic for relevance scoring <span className="text-gray-600">(optional)</span>
        </label>
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="e.g. software testing, LLM agents, security"
          className="w-full px-3 py-2 bg-gray-900 border border-gray-600 rounded text-sm text-white
                     focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
      </div>

      <div>
        <label className="block text-xs text-gray-400 mb-2">LLM Configuration</label>
        <LLMSelector value={llmConfig} onChange={setLlmConfig} />
      </div>

      <div className="flex items-center gap-2">
        <input
          id="llm-fallback"
          type="checkbox"
          checked={useLLMFallback}
          onChange={(e) => setUseLLMFallback(e.target.checked)}
          className="rounded border-gray-600 bg-gray-800"
        />
        <label htmlFor="llm-fallback" className="text-xs text-gray-400">
          Use LLM fallback for abstract extraction
        </label>
      </div>

      {error && (
        <p className="text-sm text-red-400 bg-red-900/20 border border-red-800 rounded p-2">{error}</p>
      )}

      <button
        type="submit"
        disabled={isPending}
        className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-700 text-white
                   font-medium rounded-lg transition-colors text-sm"
      >
        {isPending ? "Starting…" : "Scrape & Summarize"}
      </button>
    </form>
  );
}
