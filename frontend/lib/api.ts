export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(public readonly status: number, public readonly code: string, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: { Accept: "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    if (response.status === 401 && typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) window.location.assign("/login");
    throw new ApiError(response.status, body?.detail?.code ?? "REQUEST_FAILED", body?.detail?.message ?? "Request failed.");
  }
  return response.json() as Promise<T>;
}
