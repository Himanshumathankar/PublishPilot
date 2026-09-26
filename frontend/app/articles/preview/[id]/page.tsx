export default async function PreviewPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <main className="mx-auto max-w-[1500px] px-4 py-8 sm:px-8">
      <div className="mb-2 rounded-2xl border border-[var(--line)] bg-white px-6 py-5 shadow-sm">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-[var(--brand)]">Article workspace</p>
        <h1 className="mt-1 text-3xl font-bold">Review and publish</h1>
        <p className="mt-1 text-sm text-[var(--muted)]">Edit the story, check publishing details, and preview exactly what will be sent to WordPress.</p>
      </div>
      <ArticlePreview id={id} />
    </main>
  );
}
import { ArticlePreview } from "@/components/article-preview";
