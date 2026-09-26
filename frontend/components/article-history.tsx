"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type HistoryItem = { job_id: string; article_id?: string; title?: string; source_type: string; source_name: string; status: string; wordpress_url?: string; error_code?: string; error_message?: string; created_at: string };
type HistoryResponse = { items: HistoryItem[]; total: number; page: number; page_size: number };
const statusClass: Record<string, string> = { failed: "bg-red-100 text-red-800", published: "bg-green-100 text-green-800", draft: "bg-blue-100 text-blue-800", ready: "bg-amber-100 text-amber-800", processing: "bg-gray-100 text-gray-700" };

export function ArticleHistory() {
  const [result, setResult] = useState<HistoryResponse | null>(null);
  const [error, setError] = useState(""); const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState(""); const [sourceType, setSourceType] = useState("");
  const [searchInput, setSearchInput] = useState(""); const [search, setSearch] = useState(""); const [page, setPage] = useState(1);
  useEffect(() => {
    const params = new URLSearchParams({ page: String(page), page_size: "20" });
    if (status) params.set("status", status); if (sourceType) params.set("source_type", sourceType); if (search) params.set("search", search);
    apiRequest<HistoryResponse>(`/articles/history?${params}`).then(setResult).catch((reason) => setError(reason instanceof Error ? reason.message : "Could not load history.")).finally(() => setLoading(false));
  }, [page, search, sourceType, status]);
  function refresh(change: () => void) { setLoading(true); setError(""); change(); }
  function submitSearch(event: FormEvent) { event.preventDefault(); refresh(() => { setPage(1); setSearch(searchInput.trim()); }); }

  return <section className="mt-8">
    <form onSubmit={submitSearch} className="grid gap-3 rounded-2xl border border-[var(--line)] bg-white p-4 shadow-sm md:grid-cols-[1fr_180px_180px_auto]">
      <label className="text-sm font-semibold">Search<input aria-label="Search history" value={searchInput} onChange={(e) => setSearchInput(e.target.value)} placeholder="Title or source" className="mt-1 block w-full rounded-lg border border-[var(--line)] px-3 py-2 font-normal" /></label>
      <label className="text-sm font-semibold">Status<select aria-label="Filter by status" value={status} onChange={(e) => refresh(() => { setStatus(e.target.value); setPage(1); })} className="mt-1 block w-full rounded-lg border border-[var(--line)] px-3 py-2 font-normal"><option value="">All statuses</option><option value="processing">Processing</option><option value="ready">Ready</option><option value="draft">Draft</option><option value="published">Published</option><option value="failed">Failed</option></select></label>
      <label className="text-sm font-semibold">Source<select aria-label="Filter by source" value={sourceType} onChange={(e) => refresh(() => { setSourceType(e.target.value); setPage(1); })} className="mt-1 block w-full rounded-lg border border-[var(--line)] px-3 py-2 font-normal"><option value="">All sources</option><option value="docx">DOCX</option><option value="google_doc">Google Doc</option><option value="google_sheet">Google Sheet</option></select></label>
      <button className="self-end rounded-lg bg-[var(--brand)] px-5 py-2 font-semibold text-white">Search</button>
    </form>
    {error && <p role="alert" className="mt-6 text-red-700">{error}</p>}{loading && <p className="mt-6">Loading history…</p>}
    {!loading && result && !result.items.length && <div className="mt-6 rounded-2xl border border-[var(--line)] bg-white p-12 text-center shadow-sm"><h2 className="text-lg font-semibold">No matching records</h2><p className="mt-2 text-sm text-[var(--muted)]">Processed and failed imports will appear here.</p></div>}
    {!loading && result && result.items.length > 0 && <><div className="mt-6 overflow-x-auto rounded-2xl border border-[var(--line)] bg-white shadow-sm"><table className="w-full text-left text-sm"><thead className="border-b bg-gray-50"><tr><th className="p-4">Article</th><th className="p-4">Source</th><th className="p-4">Status</th><th className="p-4">Created</th><th className="p-4">Actions</th></tr></thead><tbody>{result.items.map((item) => <tr className="border-b align-top last:border-0" key={item.job_id}><td className="p-4"><div className="font-semibold">{item.title || "Import failed before article creation"}</div>{item.error_code && <div className="mt-1 max-w-md text-xs text-red-700">{item.error_code}: {item.error_message}</div>}</td><td className="max-w-xs break-words p-4"><div className="capitalize">{item.source_type.replaceAll("_", " ")}</div><div className="mt-1 truncate text-xs text-[var(--muted)]" title={item.source_name}>{item.source_name}</div></td><td className="p-4"><span className={`rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${statusClass[item.status] ?? statusClass.processing}`}>{item.status}</span></td><td className="whitespace-nowrap p-4">{new Date(item.created_at).toLocaleString()}</td><td className="whitespace-nowrap p-4"><Link className="font-semibold text-[var(--brand)] hover:underline" href={`/articles/history/${item.job_id}`}>Details</Link>{item.article_id && <Link className="ml-3 hover:underline" href={`/articles/preview/${item.article_id}`}>Preview</Link>}{item.wordpress_url && <a className="ml-3 hover:underline" href={item.wordpress_url} target="_blank" rel="noreferrer">WordPress</a>}</td></tr>)}</tbody></table></div><div className="mt-4 flex items-center justify-between text-sm"><span>{result.total} record{result.total === 1 ? "" : "s"}</span><div className="flex gap-2"><button disabled={page === 1} onClick={() => refresh(() => setPage((value) => value - 1))} className="rounded-lg border bg-white px-4 py-2 disabled:opacity-40">Previous</button><span className="px-2 py-2">Page {page}</span><button disabled={page * result.page_size >= result.total} onClick={() => refresh(() => setPage((value) => value + 1))} className="rounded-lg border bg-white px-4 py-2 disabled:opacity-40">Next</button></div></div></>}
  </section>;
}
