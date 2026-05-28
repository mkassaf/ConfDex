import { useQuery } from "@tanstack/react-query";
import { listJobs, type Job } from "../api/jobs";

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
}

export function JobList({ selectedId, onSelect }: Props) {
  const { data: jobs = [], isLoading } = useQuery({
    queryKey: ["jobs"],
    queryFn: listJobs,
    refetchInterval: 5_000,
  });

  if (isLoading) return <p className="text-sm text-blue-200/40 p-4">Loading…</p>;
  if (jobs.length === 0) return <p className="text-sm text-blue-200/30 p-4">No jobs yet. Start one →</p>;

  return (
    <ul className="divide-y divide-navy">
      {jobs.map((job) => (
        <li key={job.id}>
          <button
            onClick={() => onSelect(job.id)}
            className={`w-full text-left px-4 py-3 hover:bg-navy transition-colors ${
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
        </li>
      ))}
    </ul>
  );
}
