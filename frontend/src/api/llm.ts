export type EnvKeys = Record<string, boolean>;

export async function getEnvKeys(): Promise<EnvKeys> {
  const r = await fetch("/api/llm/env-keys");
  if (!r.ok) return {};
  return r.json();
}
