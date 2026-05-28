import { useEffect, useState } from "react";

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
}

export function JobProgress({ jobId, initialStatus }: Props) {
  const [state, setState] = useState<ProgressState>({
    status: initialStatus,
    progress_current: 0,
    progress_total: 0,
  });

  useEffect(() => {
    if (["done", "error"].includes(initialStatus)) return;

    const es = new EventSource(`/api/jobs/${jobId}/stream`);
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        setState(data);
        if (["done", "error"].includes(data.status)) es.close();
      } catch { /* skip */ }
    };
    es.onerror = () => es.close();
    return () => es.close();
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
        <pre className="text-xs text-red-400 bg-red-950/30 border border-red-900 rounded p-3 overflow-auto max-h-48 whitespace-pre-wrap">
          {state.error}
        </pre>
      )}
    </div>
  );
}
