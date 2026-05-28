import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { JobForm } from "./components/JobForm";
import { JobList } from "./components/JobList";
import { JobDetail } from "./components/JobDetail";
import { deleteJob } from "./api/jobs";

export default function App() {
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const qc = useQueryClient();

  const { mutate: removeJob, isPending: isDeleting } = useMutation({
    mutationFn: () => deleteJob(selectedJobId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
      setSelectedJobId(null);
    },
  });

  function handleNewJob() {
    setShowForm(true);
    setSelectedJobId(null);
  }

  function handleDelete() {
    if (confirm("Delete this job and its results?")) removeJob();
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-72 flex-shrink-0 bg-navy-dark border-r border-navy flex flex-col">

        {/* Header — logo + title only */}
        <div className="px-4 py-3 border-b border-navy">
          <div className="flex items-center gap-2.5">
            <img src="/icon.svg" alt="ConfDex" className="w-8 h-8 rounded" />
            <div>
              <h1 className="text-base font-bold text-white leading-tight">ConfDex</h1>
              <p className="text-xs text-blue-200/40">Conference paper explorer</p>
            </div>
          </div>
        </div>

        {/* Action bar */}
        <div className="px-3 py-2.5 border-b border-navy flex gap-2">
          <button
            type="button"
            onClick={handleNewJob}
            className="flex-1 py-2 bg-gold hover:bg-gold-hover text-navy-dark rounded-lg text-sm font-bold transition-colors"
          >
            + New Job
          </button>
          {selectedJobId && (
            <button
              type="button"
              onClick={handleDelete}
              disabled={isDeleting}
              title="Delete selected job"
              className="px-3 py-2 rounded-lg border border-red-900/60 text-red-400
                         hover:bg-red-950/40 hover:border-red-700 disabled:opacity-40
                         transition-colors flex items-center gap-1.5 text-sm"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              Delete
            </button>
          )}
        </div>

        {/* Job list */}
        <div className="flex-1 overflow-y-auto">
          <JobList
            selectedId={selectedJobId}
            onSelect={(id) => { setSelectedJobId(id); setShowForm(false); }}
          />
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-navy">
          <p className="text-xs text-blue-200/25 text-center">Design by Mustafa Assaf</p>
        </div>
      </aside>

      {/* Main panel */}
      <main className="flex-1 overflow-y-auto bg-navy-deeper">
        {showForm ? (
          <div className="max-w-lg mx-auto p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-white">New Scraping Job</h2>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="text-blue-200/40 hover:text-white transition-colors text-lg leading-none"
              >
                ✕
              </button>
            </div>
            <JobForm />
          </div>
        ) : selectedJobId ? (
          <JobDetail
            key={selectedJobId}
            jobId={selectedJobId}
            onDeleted={() => setSelectedJobId(null)}
          />
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <img src="/icon.svg" alt="ConfDex" className="w-24 h-24 rounded-2xl mb-5 shadow-lg" />
            <h2 className="text-xl font-semibold text-white mb-2">Welcome to ConfDex</h2>
            <p className="text-sm text-blue-200/50 mb-6 max-w-sm">
              Scrape, summarize, and find relevant papers from academic conferences.
            </p>
            <button
              type="button"
              onClick={handleNewJob}
              className="px-5 py-2.5 bg-gold hover:bg-gold-hover text-navy-dark rounded-lg font-bold transition-colors"
            >
              + New Job
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
