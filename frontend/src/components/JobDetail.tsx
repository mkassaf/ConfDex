import { useQuery } from "@tanstack/react-query";
import { getJob } from "../api/jobs";
import { JobProgress } from "./JobProgress";
import { ResultsTable } from "./ResultsTable";

interface Props {
  jobId: string;
  onDeleted: () => void;
}

export function JobDetail({ jobId }: Props) {
  const { data: job, isLoading } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "done" || status === "error" ? false : 3_000;
    },
  });

  if (isLoading) return <p className="text-blue-200/40 text-sm p-6">Loading…</p>;
  if (!job) return <p className="text-red-400 text-sm p-6">Job not found.</p>;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-lg font-semibold text-white">
          {job.conference ?? "Custom URLs"}
        </h2>
        {job.topic && <p className="text-sm text-gold mt-0.5">Topic: {job.topic}</p>}
        <p className="text-xs text-blue-200/30 mt-1">
          Model: {job.model} · Created: {new Date(job.created_at).toLocaleString()}
        </p>
      </div>

      {/* Progress */}
      <div className="bg-navy-dark rounded-lg p-4 border border-navy">
        <JobProgress
          jobId={jobId}
          initialStatus={job.status}
          initialError={job.error}
          initialPhase={job.phase}
          initialCurrent={job.progress_current}
          initialTotal={job.progress_total}
        />
      </div>

      {/* Results */}
      {job.status === "done" && job.summaries && job.summaries.length > 0 && (
        <ResultsTable summaries={job.summaries} jobId={jobId} />
      )}
      {job.status === "done" && (!job.summaries || job.summaries.length === 0) && (
        <p className="text-sm text-blue-200/40">No papers found.</p>
      )}
    </div>
  );
}
