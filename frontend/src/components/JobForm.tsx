import { useState } from "react";
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import { createJob, listJobs, type Job } from "../api/jobs";
import { getEnvKeys } from "../api/llm";
import { LLMSelector, type LLMConfig, REMOTE_PRESETS, keyRequiredFor } from "./LLMSelector";

interface Props {
  onJobCreated?: (jobId: string) => void;
}

export function JobForm({ onJobCreated }: Props) {
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
  const [duplicateJob, setDuplicateJob] = useState<Job | null>(null);

  const { data: envKeys = {} } = useQuery({
    queryKey: ["llm-env-keys"],
    queryFn: getEnvKeys,
    staleTime: 60_000,
  });

  const { data: existingJobs = [] } = useQuery({
    queryKey: ["jobs"],
    queryFn: listJobs,
    staleTime: 10_000,
  });

  const { mutate, isPending } = useMutation({
    mutationFn: createJob,
    onSuccess: (job) => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
      setError("");
      setDuplicateJob(null);
      onJobCreated?.(job.id);
    },
    onError: (e: Error) => setError(e.message),
  });

  function buildParams() {
    const track_urls =
      inputMode === "urls"
        ? urlsText.split("\n").map((u) => u.trim()).filter(Boolean)
        : undefined;
    return {
      conference: inputMode === "conference" ? conference.trim() || undefined : undefined,
      track_urls,
      topic: topic.trim() || undefined,
      model: llmConfig.model,
      api_key: llmConfig.api_key || undefined,
      use_llm_fallback: useLLMFallback,
    };
  }

  function findDuplicate(): Job | null {
    const conf = inputMode === "conference" ? conference.trim() : undefined;
    const urls = inputMode === "urls"
      ? urlsText.split("\n").map((u) => u.trim()).filter(Boolean).sort().join("\n")
      : undefined;
    const t = topic.trim();

    return existingJobs.find((j) => {
      const jobUrls = Array.isArray(j.track_urls) ? [...j.track_urls].sort().join("\n") : undefined;
      const conferenceMatch = conf ? j.conference === conf : false;
      const urlsMatch = urls ? jobUrls === urls : false;
      return (conferenceMatch || urlsMatch) && (j.topic ?? "") === t && j.model === llmConfig.model;
    }) ?? null;
  }

  function validate(): string | null {
    const track_urls = buildParams().track_urls;
    if (inputMode === "conference" && !conference.trim()) return "Please enter a conference slug.";
    if (inputMode === "urls" && (!track_urls || track_urls.length === 0)) return "Please enter at least one URL.";
    if (llmConfig.source === "remote") {
      const preset = REMOTE_PRESETS.find((p) => p.model === llmConfig.model);
      if (preset && keyRequiredFor(preset, envKeys) && !llmConfig.api_key?.trim()) {
        return `An API key is required for this provider. Enter it above or set ${preset.keyHint || "API key"} on the server.`;
      }
    }
    return null;
  }

  function handleSubmit() {
    setError("");
    setDuplicateJob(null);
    const validationError = validate();
    if (validationError) { setError(validationError); return; }

    const dup = findDuplicate();
    if (dup) { setDuplicateJob(dup); return; }

    mutate(buildParams());
  }

  function handleRerun() {
    setDuplicateJob(null);
    setError("");
    mutate(buildParams());
  }

  const inputClass = "w-full px-3 py-2 bg-navy-deeper border border-navy rounded text-sm text-white placeholder-blue-200/30 focus:outline-none focus:ring-1 focus:ring-gold";

  return (
    <div className="space-y-5">
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
          placeholder="e.g. LLM AND software testing  |  security OR privacy  |  fuzzing"
          className={inputClass}
        />
        <p className="text-xs text-blue-200/25 mt-1">
          Supports <code className="font-mono text-blue-200/40">AND</code> (all required) and{" "}
          <code className="font-mono text-blue-200/40">OR</code> (any match) — e.g.{" "}
          <span className="text-blue-200/40 font-mono">LLM AND (testing OR verification)</span>
        </p>
      </div>

      <div>
        {!envKeys["DISABLE_OLLAMA"] && (
          <label className="block text-xs text-blue-200/50 mb-2">LLM Configuration</label>
        )}
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

      {duplicateJob && (
        <div className="rounded-lg border border-gold/40 bg-gold/5 p-3 space-y-2">
          <p className="text-sm text-gold font-medium">Already scanned before</p>
          <p className="text-xs text-blue-200/50">
            This exact job was run on{" "}
            <span className="text-blue-200/80">{new Date(duplicateJob.created_at).toLocaleString()}</span>
            {duplicateJob.status === "done" && " and completed successfully"}.
          </p>
          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={() => onJobCreated?.(duplicateJob.id)}
              className="flex-1 py-2 bg-gold hover:bg-gold-hover text-navy-dark rounded-lg text-xs font-bold transition-colors"
            >
              View Results
            </button>
            <button
              type="button"
              onClick={handleRerun}
              disabled={isPending}
              className="flex-1 py-2 border border-navy hover:border-gold/40 text-blue-200/60 hover:text-white
                         rounded-lg text-xs font-medium transition-colors disabled:opacity-40"
            >
              {isPending ? "Starting…" : "Re-run Scan"}
            </button>
          </div>
        </div>
      )}

      {!duplicateJob && (
        <button
          type="button"
          onClick={handleSubmit}
          disabled={isPending}
          className="w-full py-2.5 bg-gold hover:bg-gold-hover disabled:bg-navy disabled:text-blue-200/30
                     text-navy-dark font-bold rounded-lg transition-colors text-sm"
        >
          {isPending ? "Starting…" : "Scrape & Summarize"}
        </button>
      )}
    </div>
  );
}
