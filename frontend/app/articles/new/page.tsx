import { SourceForm } from "@/components/source-form";

export default function NewArticlePage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <p className="text-sm font-semibold uppercase tracking-widest text-[var(--brand)]">Publishing workflow</p>
      <h1 className="mt-2 text-4xl font-bold tracking-tight">New article</h1>
      <p className="mt-3 max-w-2xl leading-7 text-[var(--muted)]">Import source content without rewriting it. Review every field and formatting detail before creating a WordPress draft.</p>
      <section className="mt-8 rounded-2xl border border-[var(--line)] bg-white p-6 shadow-sm sm:p-8">
        <SourceForm />
      </section>
    </main>
  );
}

