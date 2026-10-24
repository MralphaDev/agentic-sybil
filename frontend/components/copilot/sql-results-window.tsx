"use client";

import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp, Check, Copy, Download, X } from "lucide-react";

type SqlCell = string | number | boolean | null;
type SqlRow = Record<string, unknown>;

type SqlResultsWindowProps = {
  open: boolean;
  title?: string;
  description?: string;
  columns: string[];
  rows: SqlRow[];
  onClose: () => void;
};

function displayValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function toCsvCell(value: unknown): string {
  const text = displayValue(value);
  return `"${text.replaceAll('"', '""')}"`;
}

export default function SqlResultsWindow({
  open,
  title = "SQL query results",
  description = "Structured results returned by the investigation database",
  columns,
  rows,
  onClose,
}: SqlResultsWindowProps) {
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const [page, setPage] = useState(0);
  const [copiedCell, setCopiedCell] = useState<string | null>(null);
  const pageSize = 25;

  const safeColumns = useMemo(() => {
    if (columns.length) return columns;
    return rows[0] ? Object.keys(rows[0]) : [];
  }, [columns, rows]);

  const sortedRows = useMemo(() => {
    if (!sortColumn) return rows;
    return [...rows].sort((left, right) => {
      const a = left[sortColumn];
      const b = right[sortColumn];
      const aNumber = typeof a === "number" ? a : Number(a);
      const bNumber = typeof b === "number" ? b : Number(b);
      const bothNumeric =
        String(a ?? "").trim() !== "" &&
        String(b ?? "").trim() !== "" &&
        Number.isFinite(aNumber) &&
        Number.isFinite(bNumber);
      const comparison = bothNumeric
        ? aNumber - bNumber
        : displayValue(a).localeCompare(displayValue(b), undefined, {
            numeric: true,
            sensitivity: "base",
          });
      return sortDirection === "asc" ? comparison : -comparison;
    });
  }, [rows, sortColumn, sortDirection]);

  if (!open) return null;

  const pageCount = Math.max(1, Math.ceil(sortedRows.length / pageSize));
  const visibleRows = sortedRows.slice(page * pageSize, (page + 1) * pageSize);

  function toggleSort(column: string) {
    if (sortColumn === column) {
      setSortDirection((direction) => (direction === "asc" ? "desc" : "asc"));
    } else {
      setSortColumn(column);
      setSortDirection("asc");
    }
    setPage(0);
  }

  async function copyValue(value: unknown, key: string) {
    try {
      await navigator.clipboard.writeText(displayValue(value));
      setCopiedCell(key);
      window.setTimeout(() => setCopiedCell(null), 1200);
    } catch {
      setCopiedCell(null);
    }
  }

  function downloadCsv() {
    const csv = [
      safeColumns.map(toCsvCell).join(","),
      ...sortedRows.map((row) => safeColumns.map((column) => toCsvCell(row[column])).join(",")),
    ].join("\r\n");
    const url = URL.createObjectURL(new Blob(["\uFEFF", csv], { type: "text/csv;charset=utf-8;" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "sql-query-results.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/75 p-3 backdrop-blur-sm sm:p-6"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="sql-results-title"
        className="flex max-h-[92vh] w-full max-w-[1500px] flex-col overflow-hidden rounded-2xl border border-white/10 bg-[#0b0b0e] shadow-[0_30px_120px_rgba(0,0,0,0.65)]"
      >
        <header className="flex flex-wrap items-start justify-between gap-4 border-b border-white/[0.08] bg-[#101014] px-5 py-4 sm:px-7">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.2em] text-red-300">
              <span className="h-1.5 w-1.5 rounded-full bg-red-400" />
              Query workspace
            </div>
            <h2 id="sql-results-title" className="mt-2 text-lg font-semibold text-white sm:text-xl">
              {title}
            </h2>
            <p className="mt-1 text-xs text-zinc-500">{description}</p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <span className="rounded-md border border-white/[0.08] bg-white/[0.03] px-3 py-2 font-mono text-xs text-zinc-300">
              {rows.length.toLocaleString()} rows
            </span>
            <button
              type="button"
              onClick={downloadCsv}
              disabled={!safeColumns.length || !rows.length}
              className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2 text-xs text-zinc-200 transition hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Download className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Export CSV</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close SQL results"
              className="rounded-lg border border-white/10 p-2 text-zinc-400 transition hover:border-white/20 hover:text-white"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </header>

        <div className="min-h-0 flex-1 overflow-auto">
          {!safeColumns.length || !rows.length ? (
            <div className="flex min-h-64 flex-col items-center justify-center px-6 text-center">
              <div className="text-sm font-medium text-zinc-200">No rows to display</div>
              <p className="mt-2 text-xs text-zinc-500">The query returned an empty result set.</p>
            </div>
          ) : (
            <table className="w-full min-w-max border-separate border-spacing-0 text-left text-sm">
              <thead className="sticky top-0 z-10 bg-[#151519]">
                <tr>
                  <th className="w-14 border-b border-white/10 px-4 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
                    #
                  </th>
                  {safeColumns.map((column) => (
                    <th key={column} className="border-b border-white/10 px-4 py-3">
                      <button
                        type="button"
                        onClick={() => toggleSort(column)}
                        className="inline-flex max-w-[360px] items-center gap-2 whitespace-nowrap text-[10px] font-semibold uppercase tracking-[0.12em] text-zinc-400 transition hover:text-white"
                      >
                        {column.replaceAll("_", " ")}
                        {sortColumn === column && (
                          sortDirection === "asc"
                            ? <ArrowUp className="h-3 w-3 text-red-300" />
                            : <ArrowDown className="h-3 w-3 text-red-300" />
                        )}
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visibleRows.map((row, rowIndex) => (
                  <tr
                    key={`${page * pageSize + rowIndex}-${safeColumns.map((column) => displayValue(row[column])).join("|")}`}
                    className="group transition hover:bg-red-500/[0.045]"
                  >
                    <td className="border-b border-white/[0.055] px-4 py-3 text-right font-mono text-[11px] text-zinc-600">
                      {page * pageSize + rowIndex + 1}
                    </td>
                    {safeColumns.map((column) => {
                      const value = row[column] as SqlCell;
                      const rendered = displayValue(value);
                      const cellKey = `${page * pageSize + rowIndex}:${column}`;
                      const addressLike = /wallet|address|funder|signature|hash|mint/i.test(column);
                      return (
                        <td
                          key={column}
                          className={`max-w-[440px] border-b border-white/[0.055] px-4 py-3 align-top text-zinc-200 ${addressLike ? "font-mono text-xs" : "text-sm"}`}
                        >
                          <div className="flex min-w-0 items-start gap-2">
                            <span className={`min-w-0 ${addressLike ? "break-all" : "whitespace-normal"}`}>
                              {rendered}
                            </span>
                            <button
                              type="button"
                              onClick={() => void copyValue(value, cellKey)}
                              title="Copy cell value"
                              aria-label={`Copy ${column}`}
                              className="mt-0.5 shrink-0 rounded p-1 text-zinc-600 opacity-0 transition hover:bg-white/[0.08] hover:text-white focus:opacity-100 group-hover:opacity-100"
                            >
                              {copiedCell === cellKey
                                ? <Check className="h-3 w-3 text-emerald-300" />
                                : <Copy className="h-3 w-3" />}
                            </button>
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-white/[0.08] bg-[#101014] px-5 py-3 sm:px-7">
          <p className="text-xs text-zinc-500">
            {rows.length ? `Showing ${page * pageSize + 1}–${Math.min((page + 1) * pageSize, rows.length)} of ${rows.length.toLocaleString()} rows` : "0 rows"}
            {sortColumn ? ` · Sorted by ${sortColumn.replaceAll("_", " ")} (${sortDirection})` : ""}
          </p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={page === 0}
              onClick={() => setPage((current) => Math.max(0, current - 1))}
              className="rounded-md border border-white/10 px-3 py-1.5 text-xs text-zinc-300 transition hover:bg-white/[0.05] disabled:cursor-not-allowed disabled:opacity-35"
            >
              Previous
            </button>
            <span className="min-w-16 text-center font-mono text-[11px] text-zinc-500">
              {page + 1} / {pageCount}
            </span>
            <button
              type="button"
              disabled={page >= pageCount - 1}
              onClick={() => setPage((current) => Math.min(pageCount - 1, current + 1))}
              className="rounded-md border border-white/10 px-3 py-1.5 text-xs text-zinc-300 transition hover:bg-white/[0.05] disabled:cursor-not-allowed disabled:opacity-35"
            >
              Next
            </button>
          </div>
        </footer>
      </section>
    </div>
  );
}
