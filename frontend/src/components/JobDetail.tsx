import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getJob, deleteJob } from "../api/jobs";
import { JobProgress } from "./JobProgress";
import { ResultsTable } from "./ResultsTable";

interface Props {
  jobId: string;
  onDeleted: () => void;
}

export function JobDetail({ jobId, onDeleted }: Props) {
  const qc = useQueryClient();
  const { data: job, isLoading } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "done" || status === "error" ? false : 3_000;
    },
  });

  const { mutate: removeJob } = useMutation({
    mutationFn: () => deleteJob(jobId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
      onDeleted();
    },
  });

  if (isLoading) return <p className="text-gray-500 text-sm p-6">Loading…</p>;
  if (!job) return <p className="text-red-400 text-sm p-6">Job not found.</p>;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-white">
            {job.conference ?? "Custom URLs"}
          </h2>
          {job.topic && <p className="text-sm text-indigo-400 mt-0.5">Topic: {job.topic}</p>}
          <p className="text-xs text-gray-600 mt-1">
            Model: {job.model} · Created: {new Date(job.created_at).toLocaleString()}
          </p>
        </div>
        <button
          onClick={() => { if (confirm("Delete this job?")) removeJob(); }}
          className="text-xs text-red-400 hover:text-red-300 border border-red-900 hover:border-red-700
                     px-2 py-1 rounded transition-colors"
        >
          Delete
        </button>
      </div>

      {/* Progress */}
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
        <JobProgress jobId={jobId} initialStatus={job.status} />
      </div>

      {/* Results */}
      {job.status === "done" && job.summaries && job.summaries.length > 0 && (
        <ResultsTable summaries={job.summaries} jobId={jobId} />
      )}
      {job.status === "done" && (!job.summaries || job.summaries.length === 0) && (
        <p className="text-sm text-gray-500">No papers found.</p>
      )}
    </div>
  );
}
