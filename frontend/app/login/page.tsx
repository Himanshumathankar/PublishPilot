import { WordPressLogin } from "@/components/wordpress-login";

export default function LoginPage() {
  return (
    <main className="mx-auto max-w-md px-6 py-16">
      <section className="rounded-2xl border border-[var(--line)] bg-white p-8 shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-widest text-[var(--brand)]">Application login</p>
        <h1 className="mt-2 text-3xl font-bold">Welcome to TWPublisher</h1>
        <p className="mt-3 text-sm leading-6 text-[var(--muted)]">Sign in to access the publishing application. WordPress websites are managed separately from Settings.</p>
        <WordPressLogin />
      </section>
    </main>
  );
}
