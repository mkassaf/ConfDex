import { useState } from "react";
import { JobForm } from "./components/JobForm";
import { JobList } from "./components/JobList";
import { JobDetail } from "./components/JobDetail";

export default function App() {
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const showMain = showForm || selectedJobId !== null;

  function handleNewJob() {
    setShowForm(true);
    setSelectedJobId(null);
  }

  function handleBack() {
    setShowForm(false);
    setSelectedJobId(null);
  }

  return (
    <div className="flex h-screen overflow-hidden">

      {/* ── Sidebar ─────────────────────────────────────────────────────── */}
      <aside className={`
        flex-col bg-navy-dark border-r border-navy
        md:w-72 md:flex md:flex-shrink-0
        ${showMain ? "hidden md:flex" : "flex w-full"}
      `}>
        {/* Header */}
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
            className="w-full py-2.5 bg-gold hover:bg-gold-hover text-navy-dark rounded-lg text-sm font-bold transition-colors"
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

      {/* ── Main panel ──────────────────────────────────────────────────── */}
      <main className={`
        bg-navy-deeper overflow-y-auto
        md:flex-1 md:block
        ${showMain ? "flex-1 block" : "hidden md:block"}
      `}>

        {/* Mobile top bar — back button + current view title */}
        {showMain && (
          <div className="md:hidden sticky top-0 z-10 flex items-center gap-3 px-4 py-3 bg-navy-dark border-b border-navy">
            <button
              type="button"
              onClick={handleBack}
              className="flex items-center gap-1 text-gold text-sm font-medium"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              Jobs
            </button>
            <span className="text-white text-sm font-medium truncate">
              {showForm ? "New Job" : "Job Detail"}
            </span>
          </div>
        )}

        {showForm ? (
          <div className="max-w-lg mx-auto p-4 md:p-6">
            <div className="hidden md:flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-white">New Scraping Job</h2>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="text-blue-200/40 hover:text-white transition-colors text-lg leading-none"
              >
                ✕
              </button>
            </div>
            <h2 className="md:hidden text-lg font-semibold text-white mb-5">New Scraping Job</h2>
            <JobForm onJobCreated={(id) => { setSelectedJobId(id); setShowForm(false); }} />
          </div>
        ) : selectedJobId ? (
          <JobDetail
            key={selectedJobId}
            jobId={selectedJobId}
            onDeleted={() => setSelectedJobId(null)}
          />
        ) : (
          /* Desktop empty state — hidden on mobile since sidebar shows instead */
          <div className="hidden md:flex flex-col items-center justify-center h-full p-10">
            <div className="max-w-2xl w-full text-center">

              {/* Logo + brand */}
              <img src="/icon.svg" alt="ConfDex" className="w-20 h-20 rounded-2xl mx-auto mb-4 shadow-xl" />
              <h1 className="text-3xl font-bold text-white mb-1">ConfDex</h1>
              <p className="text-blue-200/60 mb-10 text-base">
                Discover research papers that matter to you — powered by AI.
              </p>

              {/* 3-step workflow */}
              <div className="grid grid-cols-3 gap-4 mb-10">
                {[
                  {
                    icon: (
                      <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
                      </svg>
                    ),
                    step: "01",
                    title: "Scrape",
                    desc: "Point at any conference slug or track URL. ConfDex discovers all papers automatically.",
                  },
                  {
                    icon: (
                      <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                      </svg>
                    ),
                    step: "02",
                    title: "Summarize",
                    desc: "Each abstract is structured by an LLM — problem, approach, result, methodology.",
                  },
                  {
                    icon: (
                      <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12" />
                      </svg>
                    ),
                    step: "03",
                    title: "Score & rank",
                    desc: "Enter your research topic and every paper is scored 0–10 for relevance. Filter instantly.",
                  },
                ].map(({ icon, step, title, desc }) => (
                  <div key={step} className="bg-navy-dark border border-navy rounded-xl p-5 text-left hover:border-gold/30 transition-colors">
                    <div className="flex items-center justify-between mb-3">
                      <div className="p-2 bg-navy rounded-lg text-gold">{icon}</div>
                      <span className="text-xs font-mono text-blue-200/20">{step}</span>
                    </div>
                    <h3 className="text-white font-semibold mb-1">{title}</h3>
                    <p className="text-xs text-blue-200/50 leading-relaxed">{desc}</p>
                  </div>
                ))}
              </div>

              {/* CTA */}
              <button
                type="button"
                onClick={handleNewJob}
                className="px-8 py-3 bg-gold hover:bg-gold-hover text-navy-dark rounded-lg font-bold text-base transition-colors shadow-lg shadow-gold/10"
              >
                + Start a New Job
              </button>
              <p className="mt-4 text-xs text-blue-200/30">
                Try: <span className="font-mono text-blue-200/50">icse-2026</span>,&nbsp;
                <span className="font-mono text-blue-200/50">ease-2026</span>,&nbsp;
                <span className="font-mono text-blue-200/50">fse-2025</span>
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
