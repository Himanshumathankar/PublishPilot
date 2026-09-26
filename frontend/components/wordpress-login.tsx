"use client";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { apiRequest } from "@/lib/api";
export function WordPressLogin() {
  const router = useRouter(); const [username, setUsername] = useState(""); const [password, setPassword] = useState(""); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  async function submit(event: FormEvent) { event.preventDefault(); setBusy(true); setError(""); try { await apiRequest("/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username, password }) }); router.push("/dashboard"); router.refresh(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not sign in."); } finally { setBusy(false); } }
  return <form onSubmit={submit} className="mt-7 space-y-4"><label className="block text-sm font-semibold">Application username<input required value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" className="mt-2 w-full rounded-lg border border-[var(--line)] px-4 py-3 font-normal" /></label><label className="block text-sm font-semibold">Application password<input required type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" className="mt-2 w-full rounded-lg border border-[var(--line)] px-4 py-3 font-normal" /></label>{error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}<button disabled={busy} className="w-full rounded-lg bg-[var(--brand)] px-5 py-3 font-semibold text-white disabled:opacity-50">{busy ? "Signing in…" : "Sign in"}</button></form>;
}
