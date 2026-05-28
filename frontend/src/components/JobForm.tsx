import { useState, useRef } from "react";
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
  const lastSubmit = useRef<{ key: string; at: number } | null>(null);

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

    const dedupKey = JSON.stringify({
      conference: inputMode === "conference" ? conference.trim() : undefined,
      track_urls,
      topic: topic.trim(),
      model: llmConfig.model,
    });
    const now = Date.now();
    if (lastSubmit.current && lastSubmit.current.key === dedupKey && now - lastSubmit.current.at < 60_000) {
      setError("This job was already submitted less than a minute ago. Please wait before resubmitting.");
      return;
    }
    lastSubmit.current = { key: dedupKey, at: now };

    mutate({
      conference: inputMode === "conference" ? conference.trim() || undefined : undefined,
      track_urls,
      topic: topic.trim() || undefined,
      model: llmConfig.model,
      api_key: llmConfig.api_key || undefined,
      use_llm_fallback: useLLMFallback,
    });
  }

  const inputClass = "w-full px-3 py-2 bg-navy-deeper border border-navy rounded text-sm text-white placeholder-blue-200/30 focus:outline-none focus:ring-1 focus:ring-gold";

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
                  ? "bg-gold border-gold text-navy-dark font-bold"
                  : "bg-navy-dark border-navy text-blue-200/50 hover:text-white"
              }`}
            >
              {m === "conference" ? "Conference slug" : "Custom URLs"}
            </button>
          ))}
        </div>

        {inputMode === "conference" ? (
          <div>
            <label className="block text-xs text-blue-200/50 mb-1">Conference slug</label>
            <input
              type="text"
              value={conference}
              onChange={(e) => setConference(e.target.value)}
              placeholder="e.g. icse-2026, fse-2025"
              required
              className={inputClass}
            />
          </div>
        ) : (
          <div>
            <label className="block text-xs text-blue-200/50 mb-1">Track URLs (one per line)</label>
            <textarea
              value={urlsText}
              onChange={(e) => setUrlsText(e.target.value)}
              rows={4}
              required
              placeholder={"https://conf.researchr.org/track/icse-2026/icse-2026-research-track\nhttps://..."}
              className={`${inputClass} resize-none font-mono`}
            />
          </div>
        )}
      </div>

      <div>
        <label className="block text-xs text-blue-200/50 mb-1">
          Topic for relevance scoring <span className="text-blue-200/30">(optional)</span>
        </label>
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="e.g. software testing, LLM agents, security"
          className={inputClass}
        />
      </div>

      <div>
        <label className="block text-xs text-blue-200/50 mb-2">LLM Configuration</label>
        <LLMSelector value={llmConfig} onChange={setLlmConfig} />
      </div>

      <div className="flex items-center gap-2">
        <input
          id="llm-fallback"
          type="checkbox"
          checked={useLLMFallback}
          onChange={(e) => setUseLLMFallback(e.target.checked)}
          className="rounded border-navy bg-navy-dark accent-gold"
        />
        <label htmlFor="llm-fallback" className="text-xs text-blue-200/50">
          Use LLM fallback for abstract extraction
        </label>
      </div>

      {error && (
        <p className="text-sm text-red-400 bg-red-900/20 border border-red-800 rounded p-2">{error}</p>
      )}

      <button
        type="submit"
        disabled={isPending}
        className="w-full py-2.5 bg-gold hover:bg-gold-hover disabled:bg-navy disabled:text-blue-200/30
                   text-navy-dark font-bold rounded-lg transition-colors text-sm"
      >
        {isPending ? "Starting…" : "Scrape & Summarize"}
      </button>
    </form>
  );
}
