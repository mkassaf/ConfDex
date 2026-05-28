import { useState, useMemo } from "react";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  useReactTable,
  type SortingState,
} from "@tanstack/react-table";
import type { Summary } from "../api/jobs";

const col = createColumnHelper<Summary>();

function ScoreBadge({ score }: { score?: number | null }) {
  if (score == null) return <span className="text-blue-200/30">—</span>;
  const color =
    score >= 8 ? "bg-green-800 text-green-200" :
    score >= 5 ? "bg-gold/20 text-gold border border-gold/30" :
    "bg-navy text-blue-200/60";
  return <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${color}`}>{score}</span>;
}

interface Props {
  summaries: Summary[];
  jobId: string;
}

export function ResultsTable({ summaries, jobId }: Props) {
  const [sorting, setSorting] = useState<SortingState>([{ id: "score", desc: true }]);
  const [filter, setFilter] = useState("");
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  const columns = useMemo(() => [
    col.accessor("score", {
      header: "Score",
      cell: (i) => <ScoreBadge score={i.getValue()} />,
      size: 60,
    }),
    col.accessor("title", {
      header: "Title",
      cell: (i) => (
        <a
          href={i.row.original.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-gold hover:text-gold-hover underline text-sm"
        >
          {i.getValue()}
        </a>
      ),
    }),
    col.accessor("domain", {
      header: "Domain",
      cell: (i) => <span className="text-xs text-blue-200/50">{i.getValue() ?? "—"}</span>,
      size: 150,
      meta: { className: "hidden md:table-cell" },
    }),
    col.accessor("methodology", {
      header: "Method",
      cell: (i) => <span className="text-xs text-blue-200/40">{i.getValue() ?? "—"}</span>,
      size: 130,
      meta: { className: "hidden md:table-cell" },
    }),
  ], []);

  const table = useReactTable({
    data: summaries,
    columns,
    state: { sorting, globalFilter: filter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  return (
    <div className="space-y-3">
      {/* Toolbar */}
      <div className="flex items-center gap-3 flex-wrap">
        <input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter by title, keyword, domain…"
          className="flex-1 min-w-48 px-3 py-1.5 bg-navy-dark border border-navy rounded text-sm text-white
                     placeholder-blue-200/30 focus:outline-none focus:ring-1 focus:ring-gold"
        />
        <span className="text-xs text-blue-200/40">{table.getRowModel().rows.length} papers</span>
        <a
          href={`/api/jobs/${jobId}/download?format=csv`}
          className="px-3 py-1.5 bg-navy-dark hover:bg-navy border border-navy rounded text-xs text-blue-200/60 hover:text-white transition-colors"
        >
          ↓ CSV
        </a>
        <a
          href={`/api/jobs/${jobId}/download?format=json`}
          className="px-3 py-1.5 bg-navy-dark hover:bg-navy border border-navy rounded text-xs text-blue-200/60 hover:text-white transition-colors"
        >
          ↓ JSON
        </a>
      </div>

      {/* Table */}
      <div className="overflow-auto rounded-lg border border-navy">
        <table className="w-full text-left text-sm">
          <thead className="bg-navy-dark text-xs text-blue-200/50 uppercase">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                <th className="px-3 py-2 w-6" />
                {hg.headers.map((h) => (
                  <th
                    key={h.id}
                    onClick={h.column.getToggleSortingHandler()}
                    className={`px-3 py-2 cursor-pointer select-none hover:text-gold whitespace-nowrap ${(h.column.columnDef.meta as any)?.className ?? ""}`}
                    style={{ width: h.column.columnDef.size }}
                  >
                    {flexRender(h.column.columnDef.header, h.getContext())}
                    {h.column.getIsSorted() === "asc" ? " ↑" : h.column.getIsSorted() === "desc" ? " ↓" : ""}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y divide-navy">
            {table.getRowModel().rows.map((row) => {
              const s = row.original;
              const isExpanded = expandedRow === row.id;
              return (
                <>
                  <tr
                    key={row.id}
                    className="hover:bg-navy/50 transition-colors cursor-pointer"
                    onClick={() => setExpandedRow(isExpanded ? null : row.id)}
                  >
                    <td className="px-3 py-2 text-blue-200/30 text-xs">{isExpanded ? "▼" : "▶"}</td>
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className={`px-3 py-2 ${(cell.column.columnDef.meta as any)?.className ?? ""}`}>
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                  {isExpanded && (
                    <tr key={`${row.id}-exp`} className="bg-navy-dark/50">
                      <td colSpan={columns.length + 1} className="px-5 py-4">
                        <div className="space-y-3 max-w-3xl">
                          {s.summary && (
                            <div>
                              <p className="text-xs text-blue-200/40 uppercase font-medium mb-1">Summary</p>
                              <p className="text-sm text-blue-50">{s.summary}</p>
                            </div>
                          )}
                          {s.score_reasoning && (
                            <div>
                              <p className="text-xs text-blue-200/40 uppercase font-medium mb-1">Relevance reasoning</p>
                              <p className="text-sm text-blue-200/70">{s.score_reasoning}</p>
                            </div>
                          )}
                          {s.score_matching && s.score_matching.length > 0 && (
                            <div>
                              <p className="text-xs text-blue-200/40 uppercase font-medium mb-1">Matching aspects</p>
                              <ul className="list-disc list-inside space-y-0.5">
                                {s.score_matching.map((m, i) => (
                                  <li key={i} className="text-sm text-gold/80">{m}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                          {s.keywords.length > 0 && (
                            <div>
                              <p className="text-xs text-blue-200/40 uppercase font-medium mb-1">Keywords</p>
                              <div className="flex flex-wrap gap-1.5">
                                {s.keywords.map((kw, i) => (
                                  <span key={i} className="text-xs px-2 py-0.5 bg-navy border border-navy-dark rounded-full text-blue-200/60">
                                    {kw}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                          {s.doi && (
                            <p className="text-xs text-blue-200/30">
                              DOI: <a href={`https://doi.org/${s.doi}`} target="_blank" rel="noopener noreferrer" className="text-gold/60 hover:underline">{s.doi}</a>
                            </p>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
