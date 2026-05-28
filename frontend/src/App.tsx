import { useState } from "react";
import { JobForm } from "./components/JobForm";
import { JobList } from "./components/JobList";
import { JobDetail } from "./components/JobDetail";

export default function App() {
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-72 flex-shrink-0 bg-navy-dark border-r border-navy flex flex-col">
        <div className="p-4 border-b border-navy flex items-center justify-between">
          <div className="flex items-center gap-2">
            <img src="/icon.svg" alt="ConfDex" className="w-8 h-8 rounded" />
            <div>
              <h1 className="text-lg font-bold text-white">ConfDex</h1>
              <p className="text-xs text-blue-200/50">Conference paper explorer</p>
            </div>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className="p-2 rounded-lg bg-gold hover:bg-gold-hover text-navy-dark transition-colors text-sm font-bold"
            title="New job"
          >
            + New
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          <JobList
            selectedId={selectedJobId}
            onSelect={(id) => { setSelectedJobId(id); setShowForm(false); }}
          />
        </div>
        <div className="p-4 border-t border-navy">
          <p className="text-xs text-blue-200/30 text-center">Design by Mustafa Assaf</p>
        </div>
      </aside>

      {/* Main panel */}
      <main className="flex-1 overflow-y-auto bg-navy-deeper">
        {showForm ? (
          <div className="max-w-lg mx-auto p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-white">New Scraping Job</h2>
              <button onClick={() => setShowForm(false)} className="text-blue-200/50 hover:text-white">✕</button>
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
              onClick={() => setShowForm(true)}
              className="px-5 py-2.5 bg-gold hover:bg-gold-hover text-navy-dark rounded-lg font-bold transition-colors"
            >
              Start a new job
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
