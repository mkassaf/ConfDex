import { useEffect, useState } from "react";

function ErrorDetail({ error }: { error: string }) {
  const lines = error.trim().split("\n");
  const raw = [...lines].reverse().find((l: string) => l.trim().length > 0) ?? error;
  const summary = raw.replace(/^[\w.]+Error:\s*/, "");
  return (
    <p className="text-sm text-red-400 bg-red-950/30 border border-red-900 rounded p-3">
      {summary}
    </p>
  );
}

interface ProgressState {
  status: string;
  phase?: string;
  progress_current: number;
  progress_total: number;
  error?: string;
}

interface Props {
  jobId: string;
  initialStatus: string;
  initialError?: string;
  initialPhase?: string;
  initialCurrent?: number;
  initialTotal?: number;
}

export function JobProgress({ jobId, initialStatus, initialError, initialPhase, initialCurrent = 0, initialTotal = 0 }: Props) {
  const [state, setState] = useState<ProgressState>({
    status: initialStatus,
    phase: initialPhase,
    error: initialError,
    progress_current: initialCurrent,
    progress_total: initialTotal,
  });

  // Sync baseline from props (covers already-finished jobs and polling fallback)
  useEffect(() => {
    setState((prev) => ({
      status: initialStatus,
      phase: initialPhase ?? prev.phase,
      error: initialError ?? prev.error,
      progress_current: initialCurrent ?? prev.progress_current,
      progress_total: initialTotal ?? prev.progress_total,
    }));
  }, [initialStatus, initialError, initialPhase, initialCurrent, initialTotal]);

  // SSE for sub-second updates while job is running
  useEffect(() => {
    if (["done", "error"].includes(initialStatus)) return;

    let es: EventSource | null = null;
    let cancelled = false;

    function connect() {
      if (cancelled) return;
      es = new EventSource(`/api/jobs/${jobId}/stream`);
      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          setState(data);
          if (["done", "error"].includes(data.status)) es?.close();
        } catch { /* skip */ }
      };
      es.onerror = () => {
        es?.close();
        if (!cancelled) setTimeout(connect, 2_000);
      };
    }

    connect();
    return () => { cancelled = true; es?.close(); };
  }, [jobId, initialStatus]);

  const pct = state.progress_total > 0
    ? Math.round((state.progress_current / state.progress_total) * 100)
    : null;

  const statusColor: Record<string, string> = {
    pending:     "text-blue-200/50",
    scraping:    "text-gold",
    summarizing: "text-gold",
    done:        "text-green-400",
    error:       "text-red-400",
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <span className={`font-semibold capitalize ${statusColor[state.status] ?? "text-blue-200/50"}`}>
          {state.status}
        </span>
        {state.phase && <span className="text-sm text-blue-200/50">{state.phase}</span>}
        {pct !== null && (
          <span className="ml-auto text-sm text-blue-200/40">{pct}%</span>
        )}
      </div>

      {["scraping", "summarizing", "pending"].includes(state.status) && (
        <div className="w-full bg-navy-deeper rounded-full h-2">
          <div
            className="bg-gold h-2 rounded-full transition-all"
            style={{
              width: pct !== null ? `${pct}%` : "5%",
              animation: pct === null ? "pulse 1.5s infinite" : undefined,
            }}
          />
        </div>
      )}

      {state.status === "error" && state.error && (
        <ErrorDetail error={state.error} />
      )}
    </div>
  );
}
