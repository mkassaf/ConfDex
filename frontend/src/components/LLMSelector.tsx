import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getOllamaModels, getOllamaStatus } from "../api/ollama";
import { getEnvKeys, type EnvKeys } from "../api/llm";
import { OllamaInstaller } from "./OllamaInstaller";

export interface LLMConfig {
  model: string;
  api_key?: string;
  source: "local" | "remote";
}

interface Props {
  value: LLMConfig;
  onChange: (v: LLMConfig) => void;
}

export const REMOTE_PRESETS = [
  { label: "Anthropic Claude (Sonnet 4.6)", model: "claude-sonnet-4-6", keyHint: "ANTHROPIC_API_KEY" },
  { label: "Anthropic Claude (Opus 4.7)", model: "claude-opus-4-7", keyHint: "ANTHROPIC_API_KEY" },
  { label: "OpenAI GPT-4o", model: "gpt-4o", keyHint: "OPENAI_API_KEY" },
  { label: "OpenAI GPT-4o Mini", model: "gpt-4o-mini", keyHint: "OPENAI_API_KEY" },
  { label: "DeepSeek Chat", model: "deepseek/deepseek-chat", keyHint: "DEEPSEEK_API_KEY" },
  { label: "DeepSeek R1", model: "deepseek/deepseek-r1", keyHint: "DEEPSEEK_API_KEY" },
  { label: "Google Gemini 1.5 Pro", model: "gemini/gemini-1.5-pro", keyHint: "GEMINI_API_KEY" },
  { label: "Google Gemini 2.0 Flash", model: "gemini/gemini-2.0-flash", keyHint: "GEMINI_API_KEY" },
  { label: "Groq Llama 3.3 70B", model: "groq/llama-3.3-70b-versatile", keyHint: "GROQ_API_KEY" },
  { label: "Mistral Large", model: "mistral/mistral-large-latest", keyHint: "MISTRAL_API_KEY" },
  { label: "Custom / Other", model: "", keyHint: "" },
];

export function keyRequiredFor(preset: typeof REMOTE_PRESETS[number], envKeys: EnvKeys): boolean {
  if (!preset.keyHint) return false; // custom — optional
  return !envKeys[preset.keyHint];   // required only if NOT set on server
}

export function LLMSelector({ value, onChange }: Props) {
  const [showInstaller, setShowInstaller] = useState(false);
  const [selectedPreset, setSelectedPreset] = useState(REMOTE_PRESETS[0].model);

  const { data: envKeys = {} } = useQuery({
    queryKey: ["llm-env-keys"],
    queryFn: getEnvKeys,
    staleTime: 60_000,
  });

  const { data: ollamaStatus } = useQuery({
    queryKey: ["ollama-status"],
    queryFn: getOllamaStatus,
    refetchInterval: 10_000,
  });

  const { data: ollamaModels = [], refetch: refetchModels } = useQuery({
    queryKey: ["ollama-models"],
    queryFn: getOllamaModels,
    enabled: value.source === "local",
  });

  function setSource(src: "local" | "remote") {
    if (src === "local") {
      onChange({ source: "local", model: `ollama/${ollamaModels[0] ?? "llama3.2"}`, api_key: undefined });
    } else {
      const preset = REMOTE_PRESETS[0];
      onChange({ source: "remote", model: preset.model, api_key: "" });
    }
  }

  function handlePresetChange(presetModel: string) {
    setSelectedPreset(presetModel);
    onChange({ ...value, model: presetModel === "" ? "" : presetModel });
  }

  const keyHint = REMOTE_PRESETS.find((p) => p.model === selectedPreset)?.keyHint ?? "";

  return (
    <div className="space-y-3">
      {/* Source toggle */}
      <div className="flex gap-2">
        {(["local", "remote"] as const).map((src) => (
          <button
            key={src}
            type="button"
            onClick={() => setSource(src)}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors border ${
              value.source === src
                ? "bg-blue-600 border-blue-500 text-white"
                : "bg-gray-800 border-gray-700 text-gray-400 hover:text-white"
            }`}
          >
            {src === "local" ? "🖥  Local (Ollama)" : "☁  Remote API"}
          </button>
        ))}
      </div>

      {/* Local — Ollama */}
      {value.source === "local" && (
        <div className="space-y-2">
          {ollamaStatus?.running === false && (
            <div className="text-xs text-yellow-400 bg-yellow-900/30 border border-yellow-700 rounded p-2">
              Ollama is not running. Start it with: <code className="font-mono">ollama serve</code>
            </div>
          )}
          <label className="block text-xs text-gray-400 mb-1">Installed model</label>
          {ollamaModels.length > 0 ? (
            <select
              value={value.model}
              onChange={(e) => onChange({ ...value, model: e.target.value })}
              className="w-full px-3 py-2 bg-gray-900 border border-gray-600 rounded text-sm text-white
                         focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {ollamaModels.map((m) => (
                <option key={m} value={`ollama/${m}`}>{m}</option>
              ))}
            </select>
          ) : (
            <p className="text-xs text-gray-500">No models installed yet. Use the installer below.</p>
          )}
          <button
            type="button"
            onClick={() => setShowInstaller(!showInstaller)}
            className="text-xs text-blue-400 hover:text-blue-300 underline"
          >
            {showInstaller ? "Hide installer" : "Install a model…"}
          </button>
          {showInstaller && (
            <OllamaInstaller
              onInstalled={() => { refetchModels(); setShowInstaller(false); }}
            />
          )}
        </div>
      )}

      {/* Remote */}
      {value.source === "remote" && (
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Provider / Model</label>
            <select
              value={selectedPreset}
              onChange={(e) => handlePresetChange(e.target.value)}
              className="w-full px-3 py-2 bg-navy-deeper border border-navy rounded text-sm text-white
                         focus:outline-none focus:ring-1 focus:ring-gold"
            >
              {REMOTE_PRESETS.map((p) => {
                const keySet = p.keyHint ? envKeys[p.keyHint] : true;
                return (
                  <option key={p.model} value={p.model}>
                    {p.label}{keySet ? " ✓" : ""}
                  </option>
                );
              })}
            </select>
          </div>
          {selectedPreset === "" && (
            <div>
              <label className="block text-xs text-blue-200/50 mb-1">Model string (litellm format)</label>
              <input
                type="text"
                value={value.model}
                onChange={(e) => onChange({ ...value, model: e.target.value })}
                placeholder="e.g. groq/mixtral-8x7b-32768"
                className="w-full px-3 py-2 bg-navy-deeper border border-navy rounded text-sm text-white
                           focus:outline-none focus:ring-1 focus:ring-gold"
              />
            </div>
          )}

          {/* API key section */}
          {(() => {
            const preset = REMOTE_PRESETS.find((p) => p.model === selectedPreset);
            const required = preset ? keyRequiredFor(preset, envKeys) : false;
            const keySet = preset?.keyHint ? envKeys[preset.keyHint] : false;

            if (keySet && !required) {
              return (
                <div className="flex items-center gap-2 text-xs text-green-400 bg-green-950/30 border border-green-900 rounded px-3 py-2">
                  <span>✓</span>
                  <span><code className="font-mono">{preset?.keyHint}</code> is set on the server — no key needed.</span>
                </div>
              );
            }

            return (
              <div>
                <label className="block text-xs mb-1">
                  <span className={required ? "text-gold font-medium" : "text-blue-200/50"}>
                    API Key{required ? " (required)" : ""}
                  </span>
                  {keyHint && !required && (
                    <span className="ml-1 text-blue-200/30">
                      or set <code className="font-mono">{keyHint}</code> on server
                    </span>
                  )}
                </label>
                <input
                  type="password"
                  value={value.api_key ?? ""}
                  onChange={(e) => onChange({ ...value, api_key: e.target.value })}
                  placeholder={required ? "Required — enter your API key" : "Optional if set as env var"}
                  className={`w-full px-3 py-2 bg-navy-deeper border rounded text-sm text-white
                             focus:outline-none focus:ring-1 focus:ring-gold
                             ${required && !value.api_key ? "border-gold/60" : "border-navy"}`}
                />
                <p className="text-xs text-blue-200/20 mt-1">Key is sent to this server only, never stored permanently.</p>
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
}
