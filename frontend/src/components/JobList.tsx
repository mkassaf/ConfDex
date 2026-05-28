import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listJobs, deleteJob, type Job } from "../api/jobs";

const STATUS_STYLES: Record<string, string> = {
  pending:     "bg-navy text-blue-200",
  scraping:    "bg-navy text-gold",
  summarizing: "bg-navy text-gold",
  done:        "bg-green-800 text-green-200",
  error:       "bg-red-800 text-red-200",
};

function StatusBadge({ status }: { status: Job["status"] }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_STYLES[status] ?? "bg-navy text-blue-200"}`}>
      {status}
    </span>
  );
}

interface Props {
  selectedId: string | null;
  onSelect: (id: string) => void;
  onDeleted?: (id: string) => void;
}

function TrashIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
    </svg>
  );
}

export function JobList({ selectedId, onSelect, onDeleted }: Props) {
  const qc = useQueryClient();
  const { data: jobs = [], isLoading } = useQuery({
    queryKey: ["jobs"],
    queryFn: listJobs,
    refetchInterval: 5_000,
  });

  const { mutate: remove } = useMutation({
    mutationFn: (id: string) => deleteJob(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
      onDeleted?.(id);
    },
  });

  function handleDelete(e: React.MouseEvent, id: string) {
    e.stopPropagation();
    if (confirm("Delete this job and its results?")) remove(id);
  }

  if (isLoading) return <p className="text-sm text-blue-200/40 p-4">Loading…</p>;
  if (jobs.length === 0) return <p className="text-sm text-blue-200/30 p-4">No jobs yet. Start one →</p>;

  return (
    <ul className="divide-y divide-navy">
      {jobs.map((job) => (
        <li key={job.id} className="group relative">
          <button
            type="button"
            onClick={() => onSelect(job.id)}
            className={`w-full text-left px-4 py-3 pr-10 hover:bg-navy transition-colors ${
              selectedId === job.id ? "bg-navy border-l-2 border-gold" : ""
            }`}
          >
            <div className="flex items-center justify-between gap-2 mb-1">
              <StatusBadge status={job.status} />
              <span className="text-xs text-blue-200/30">{new Date(job.created_at).toLocaleString()}</span>
            </div>
            <p className="text-sm text-white font-medium truncate">
              {job.conference ?? "Custom URLs"}
            </p>
            {job.topic && (
              <p className="text-xs text-gold/70 truncate">Topic: {job.topic}</p>
            )}
            {["scraping", "summarizing"].includes(job.status) && (
              <div className="mt-1.5">
                <div className="w-full bg-navy-deeper rounded-full h-1">
                  <div
                    className="bg-gold h-1 rounded-full transition-all"
                    style={{
                      width: job.progress_total > 0
                        ? `${Math.round((job.progress_current / job.progress_total) * 100)}%`
                        : "10%",
                    }}
                  />
                </div>
              </div>
            )}
          </button>

          {/* Delete — always visible on mobile (no hover), hover-only on desktop */}
          <button
            type="button"
            onClick={(e) => handleDelete(e, job.id)}
            title="Delete job"
            className="absolute right-2 top-1/2 -translate-y-1/2
                       opacity-30 md:opacity-0 md:group-hover:opacity-100 transition-opacity
                       p-1.5 rounded text-blue-200/50 hover:text-red-400 hover:bg-red-950/40"
          >
            <TrashIcon />
          </button>
        </li>
      ))}
    </ul>
  );
}
