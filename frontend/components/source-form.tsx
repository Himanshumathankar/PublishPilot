"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { API_URL } from "@/lib/api";

export function SourceForm() {
  const [filename, setFilename] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [sourceUrl, setSourceUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  async function processArticle(event: React.FormEvent) {
    event.preventDefault();
    if (!file && !sourceUrl) return;
    setBusy(true); setError("");
    try {
      let response: Response;
      if (file) {
        const form = new FormData(); form.append("file", file);
        response = await fetch(`${API_URL}/articles/process`, { method: "POST", body: form, credentials: "include" });
      } else {
        const endpoint = sourceUrl.includes("/spreadsheets/") ? "process-google-sheet" : "process-google-doc";
        response = await fetch(`${API_URL}/articles/${endpoint}`, {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url: sourceUrl }), credentials: "include",
        });
      }
      const body = await response.json();
      if (response.status === 401) { router.push("/login"); return; }
      if (!response.ok) throw new Error(body?.detail?.message ?? "Article processing failed.");
      router.push(`/articles/preview/${body.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Article processing failed.");
    } finally { setBusy(false); }
  }

  return (
    <form className="mt-8 space-y-7" onSubmit={processArticle}>
      <fieldset className="space-y-3">
        <legend className="text-sm font-semibold">Article source</legend>
        <label className="flex min-h-32 cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-[var(--line)] bg-[#fafbf8] px-6 text-center hover:border-[var(--brand)]">
          <span className="font-semibold">Upload DOCX</span>
          <span className="mt-1 text-sm text-[var(--muted)]">{filename || "Microsoft Word .docx, up to 25 MB"}</span>
          <input aria-label="Upload DOCX" className="sr-only" type="file" accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={(event) => { const selected = event.target.files?.[0] ?? null; setFile(selected); setFilename(selected?.name ?? ""); if (selected) setSourceUrl(""); }} />
        </label>
        <div className="flex items-center gap-3 text-xs uppercase tracking-widest text-[var(--muted)]"><span className="h-px flex-1 bg-[var(--line)]" />or<span className="h-px flex-1 bg-[var(--line)]" /></div>
        <input value={sourceUrl} onChange={(event) => { setSourceUrl(event.target.value); if (event.target.value) { setFile(null); setFilename(""); } }} aria-label="Google document or sheet URL" placeholder="Paste a Google Docs or Google Sheets URL" className="w-full rounded-lg border border-[var(--line)] px-4 py-3 text-sm" />
      </fieldset>

      {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      <button disabled={(!filename && !sourceUrl) || busy} className="w-full rounded-lg bg-[var(--brand)] px-5 py-3 font-semibold text-white transition hover:bg-[var(--brand-dark)] disabled:cursor-not-allowed disabled:opacity-40">{busy ? "Processing…" : "Process article"}</button>
      <p className="text-center text-xs text-[var(--muted)]">The source is parsed deterministically. No article content is rewritten.</p>
    </form>
  );
}
