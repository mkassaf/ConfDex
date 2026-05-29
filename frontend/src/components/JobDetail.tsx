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

  const isDone = job.status === "done";
  const isError = job.status === "error";
  const paperCount = job.progress_total ?? job.summaries?.length ?? 0;

  return (
    <div className="p-4 md:p-6 space-y-5 md:space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold text-white truncate">
            {job.conference ?? "Custom URLs"}
          </h2>
          {job.topic && <p className="text-sm text-gold mt-0.5 truncate">Topic: {job.topic}</p>}
          <p className="text-xs text-blue-200/30 mt-1">
            Model: {job.model} · {new Date(job.created_at).toLocaleString()}
          </p>
        </div>

        {/* Compact status badge — only shown when finished */}
        {isDone && (
          <span className="shrink-0 flex items-center gap-1.5 text-xs font-medium text-green-400
                           bg-green-950/40 border border-green-900/60 rounded-full px-3 py-1">
            <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            {paperCount > 0 ? `${paperCount} papers` : "Done"}
          </span>
        )}
        {isError && (
          <span className="shrink-0 text-xs font-medium text-red-400
                           bg-red-950/40 border border-red-900/60 rounded-full px-3 py-1">
            Failed
          </span>
        )}
      </div>

      {/* Progress card — only shown while running or on error */}
      {!isDone && (
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
      )}

      {/* Results */}
      {isDone && job.summaries && job.summaries.length > 0 && (
        <ResultsTable summaries={job.summaries} jobId={jobId} />
      )}
      {isDone && (!job.summaries || job.summaries.length === 0) && (
        <p className="text-sm text-blue-200/40">No papers found.</p>
      )}
    </div>
  );
}
