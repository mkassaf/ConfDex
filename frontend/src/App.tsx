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
      <aside className="w-72 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col">
        <div className="p-4 border-b border-gray-800 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-white">ConfDex</h1>
            <p className="text-xs text-gray-500">Conference paper explorer</p>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className="p-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white transition-colors text-sm font-medium"
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
        <div className="p-4 border-t border-gray-800">
          <p className="text-xs text-gray-600 text-center">Design by Mustafa Assaf</p>
        </div>
      </aside>

      {/* Main panel */}
      <main className="flex-1 overflow-y-auto">
        {showForm ? (
          <div className="max-w-lg mx-auto p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-white">New Scraping Job</h2>
              <button onClick={() => setShowForm(false)} className="text-gray-500 hover:text-white">✕</button>
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
            <p className="text-5xl mb-4">📄</p>
            <h2 className="text-xl font-semibold text-gray-300 mb-2">Welcome to ConfDex</h2>
            <p className="text-sm text-gray-500 mb-6 max-w-sm">
              Scrape, summarize, and find relevant papers from academic conferences.
            </p>
            <button
              onClick={() => setShowForm(true)}
              className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors"
            >
              Start a new job
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
