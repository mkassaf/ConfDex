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
  abstract?: string;
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

const STATUS_MESSAGES: Record<number, string> = {
  400: "Invalid request — check your inputs.",
  401: "Authentication required. Check your credentials.",
  403: "Access denied.",
  404: "Not found.",
  422: "Invalid parameters sent to server.",
  429: "Too many requests. Please wait and try again.",
  500: "Server error — check the server logs.",
  502: "Server is unavailable. Is it running?",
  503: "Server is starting up. Please wait a moment.",
};

async function httpError(r: Response): Promise<Error> {
  const body = await r.json().catch(() => ({}));
  const detail = body?.detail;
  const fallback = STATUS_MESSAGES[r.status] ?? `Unexpected error (HTTP ${r.status})`;
  return new Error(typeof detail === "string" ? detail : fallback);
}

export async function createJob(params: CreateJobParams): Promise<Job> {
  let r: Response;
  try {
    r = await fetch(BASE, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    });
  } catch {
    throw new Error("Cannot reach the server. Check your network connection.");
  }
  if (!r.ok) throw await httpError(r);
  return r.json();
}

export async function listJobs(): Promise<Job[]> {
  let r: Response;
  try {
    r = await fetch(BASE);
  } catch {
    throw new Error("Cannot reach the server. Check your network connection.");
  }
  if (!r.ok) throw await httpError(r);
  return r.json();
}

export async function getJob(id: string): Promise<Job> {
  const r = await fetch(`${BASE}/${id}`);
  if (!r.ok) throw await httpError(r);
  return r.json();
}

export async function deleteJob(id: string): Promise<void> {
  const r = await fetch(`${BASE}/${id}`, { method: "DELETE" });
  if (!r.ok) throw await httpError(r);
}

export function downloadUrl(id: string, format: "json" | "csv"): string {
  return `${BASE}/${id}/download?format=${format}`;
}
