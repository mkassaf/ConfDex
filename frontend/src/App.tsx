import { useState } from "react";
import { JobForm } from "./components/JobForm";
import { JobList } from "./components/JobList";
import { JobDetail } from "./components/JobDetail";

export default function App() {
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  function handleNewJob() {
    setShowForm(true);
    setSelectedJobId(null);
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
        <div className="px-3 py-2.5 border-b border-navy">
          <button
            type="button"
            onClick={handleNewJob}
            className="w-full py-2 bg-gold hover:bg-gold-hover text-navy-dark rounded-lg text-sm font-bold transition-colors"
          >
            + New Job
          </button>
        </div>

        {/* Job list */}
        <div className="flex-1 overflow-y-auto">
          <JobList
            selectedId={selectedJobId}
            onSelect={(id) => { setSelectedJobId(id); setShowForm(false); }}
            onDeleted={(id) => { if (selectedJobId === id) setSelectedJobId(null); }}
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
