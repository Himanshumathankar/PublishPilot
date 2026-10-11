"use client";
import { FormEvent, useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";
type Site = {
  id: string;
  name: string;
  base_url: string;
  username: string;
  active: boolean;
};
type Integrations = {
  wordpress_sites: Site[];
  google_application_credentials?: string;
};
export function IntegrationSettingsForm() {
  const [data, setData] = useState<Integrations | null>(null);
  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [rankMath, setRankMath] = useState("");
  const [googlePath, setGooglePath] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function load() {
    const value = await apiRequest<Integrations>("/integrations");
    setData(value);
    setGooglePath(
      value.google_application_credentials ||
        "/run/secrets/google-service-account.json",
    );
  }
  useEffect(() => {
    load().catch((reason) => setError(reason.message));
  }, []);
  async function addSite(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await apiRequest("/integrations/wordpress-sites", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          base_url: baseUrl,
          username,
          application_password: password,
          rank_math_endpoint: rankMath || null,
        }),
      });
      setName("");
      setBaseUrl("");
      setUsername("");
      setPassword("");
      setRankMath("");
      await load();
      setMessage("Publishing website connected.");
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Could not connect website.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function saveGoogle(event: FormEvent) {
    event.preventDefault();
    setError("");
    await apiRequest("/integrations/content", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        rank_math_endpoint: null,
        google_application_credentials: googlePath || null,
      }),
    });
    setMessage("Google settings saved.");
  }
  return (
    <div className="mt-8 grid gap-6">
      <section className="rounded-2xl border border-[var(--line)] bg-white p-6 shadow-sm">
        <h2 className="text-xl font-bold">Publishing websites</h2>
        <p className="mt-2 text-sm text-[var(--muted)]">
          Add each WordPress website once, then select it while publishing.
        </p>
        <div className="mt-5 space-y-3">
          {data?.wordpress_sites
            .filter((site) => site.active)
            .map((site) => (
              <div
                key={site.id}
                className="flex items-center justify-between rounded-xl border p-4"
              >
                <div>
                  <strong>{site.name}</strong>
                  <p className="text-sm text-[var(--muted)]">
                    {site.base_url} · {site.username}
                  </p>
                </div>
                <button
                  onClick={async () => {
                    await apiRequest(
                      `/integrations/wordpress-sites/${site.id}`,
                      { method: "DELETE" },
                    );
                    await load();
                  }}
                  className="rounded-lg border px-3 py-2 text-sm text-red-700"
                >
                  Remove
                </button>
              </div>
            ))}
        </div>
        <form onSubmit={addSite} className="mt-6 grid gap-4 border-t pt-5">
          <h3 className="font-bold">Add website</h3>
          <label className="text-sm font-semibold">
            Website name
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Colitco"
              className="mt-1 w-full rounded-lg border px-4 py-3 font-normal"
            />
          </label>
          <label className="text-sm font-semibold">
            WordPress website URL
            <input
              required
              type="url"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="https://example.com"
              className="mt-1 w-full rounded-lg border px-4 py-3 font-normal"
            />
          </label>
          <label className="text-sm font-semibold">
            WordPress username
            <input
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="mt-1 w-full rounded-lg border px-4 py-3 font-normal"
            />
          </label>
          <label className="text-sm font-semibold">
            Application password
            <input
              required
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-lg border px-4 py-3 font-normal"
            />
          </label>
          <label className="text-sm font-semibold">
            Rank Math endpoint (optional)
            <input
              value={rankMath}
              onChange={(e) => setRankMath(e.target.value)}
            placeholder="/wp-json/twpublisher/v1/rank-math"
              className="mt-1 w-full rounded-lg border px-4 py-3 font-normal"
            />
          </label>
          <button
            disabled={busy}
            className="rounded-lg bg-[var(--brand)] px-5 py-3 font-semibold text-white"
          >
            {busy ? "Verifying…" : "Connect website"}
          </button>
        </form>
      </section>
      <form
        onSubmit={saveGoogle}
        className="rounded-2xl border border-[var(--line)] bg-white p-6 shadow-sm"
      >
        <h2 className="text-xl font-bold">Google integration</h2>
        <label className="mt-5 block text-sm font-semibold">
          Service-account credential path
          <input
            value={googlePath}
            onChange={(e) => setGooglePath(e.target.value)}
            className="mt-2 w-full rounded-lg border px-4 py-3 font-normal"
          />
        </label>
        <button className="mt-5 rounded-lg bg-[var(--brand)] px-5 py-3 font-semibold text-white">
          Save Google settings
        </button>
      </form>
      {error && (
        <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>
      )}
      {message && (
        <p className="rounded-lg bg-green-50 p-3 text-sm text-green-700">
          {message}
        </p>
      )}
    </div>
  );
}
