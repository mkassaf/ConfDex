export interface Job {
  id: string;
  created_at: string;
  updated_at: string;
  status: "pending" | "scraping" | "summarizing" | "done" | "error";
  conference?: string;
  track_urls?: string[];
  topic?: string;
  model: string;
  phase?: string;
  progress_current: number;
  progress_total: number;
  error?: string;
  summaries?: Summary[];
}

export interface Summary {
  title: string;
  source_url: string;
  doi?: string;
  summary?: string;
  keywords: string[];
  methodology?: string;
  domain?: string;
  score?: number;
  score_reasoning?: string;
  score_matching?: string[];
}

export interface CreateJobParams {
  conference?: string;
  track_urls?: string[];
  topic?: string;
  model: string;
  api_key?: string;
  use_llm_fallback?: boolean;
}

const BASE = "/api/jobs";

export async function createJob(params: CreateJobParams): Promise<Job> {
  const r = await fetch(BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${r.status}`);
  }
  return r.json();
}

export async function listJobs(): Promise<Job[]> {
  const r = await fetch(BASE);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function getJob(id: string): Promise<Job> {
  const r = await fetch(`${BASE}/${id}`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function deleteJob(id: string): Promise<void> {
  const r = await fetch(`${BASE}/${id}`, { method: "DELETE" });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
}

export function downloadUrl(id: string, format: "json" | "csv"): string {
  return `${BASE}/${id}/download?format=${format}`;
}
