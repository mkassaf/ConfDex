import { useQuery } from "@tanstack/react-query";
import { listJobs, type Job } from "../api/jobs";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-gray-700 text-gray-300",
  scraping: "bg-blue-800 text-blue-200",
  summarizing: "bg-indigo-800 text-indigo-200",
  done: "bg-green-800 text-green-200",
  error: "bg-red-800 text-red-200",
};

function StatusBadge({ status }: { status: Job["status"] }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_STYLES[status] ?? "bg-gray-700 text-gray-300"}`}>
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

  if (isLoading) return <p className="text-sm text-gray-500 p-4">Loading…</p>;
  if (jobs.length === 0) return <p className="text-sm text-gray-600 p-4">No jobs yet. Start one →</p>;

  return (
    <ul className="divide-y divide-gray-800">
      {jobs.map((job) => (
        <li key={job.id}>
          <button
            onClick={() => onSelect(job.id)}
            className={`w-full text-left px-4 py-3 hover:bg-gray-800 transition-colors ${
              selectedId === job.id ? "bg-gray-800 border-l-2 border-indigo-500" : ""
            }`}
          >
            <div className="flex items-center justify-between gap-2 mb-1">
              <StatusBadge status={job.status} />
              <span className="text-xs text-gray-600">{new Date(job.created_at).toLocaleString()}</span>
            </div>
            <p className="text-sm text-white font-medium truncate">
              {job.conference ?? "Custom URLs"}
            </p>
            {job.topic && (
              <p className="text-xs text-indigo-400 truncate">Topic: {job.topic}</p>
            )}
            {["scraping", "summarizing"].includes(job.status) && (
              <div className="mt-1.5">
                <div className="w-full bg-gray-700 rounded-full h-1">
                  <div
                    className="bg-indigo-500 h-1 rounded-full transition-all"
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
