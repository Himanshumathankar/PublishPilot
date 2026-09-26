export default function HistoryPage() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      <p className="text-sm font-semibold uppercase tracking-widest text-[var(--brand)]">Audit trail</p>
      <h1 className="mt-2 text-4xl font-bold tracking-tight">Article history</h1>
      <ArticleHistory />
    </main>
  );
}
import { ArticleHistory } from "@/components/article-history";

