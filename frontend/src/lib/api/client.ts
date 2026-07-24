import type { Page } from "./types";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public fields: Record<string, string[]> = {},
  ) {
    super(message);
  }
}
function messageFor(status: number, body: unknown) {
  if (body && typeof body === "object") {
    const r = body as Record<string, unknown>;
    const raw = r.detail ?? r.non_field_errors;
    if (typeof raw === "string") return raw;
    if (Array.isArray(raw)) return raw.join(" ");
  }
  return status === 403
    ? "You do not have permission to do that."
    : status === 404
      ? "That record was not found."
      : status === 429
        ? "Too many requests. Please wait and try again."
        : status >= 500
          ? "The service is temporarily unavailable."
          : "Please check the highlighted fields.";
}
export async function api<T>(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData) && init.body)
    headers.set("Content-Type", "application/json");
  const normalizedPath = path.replace(/^\//, "").replace(/\/(?=\?|$)/, "");
  const response = await fetch(`/api/backend/${normalizedPath}`, {
    ...init,
    headers,
    credentials: "same-origin",
  });
  if (!response.ok) {
    let body: unknown = {};
    try {
      body = await response.json();
    } catch {}
    const fields: Record<string, string[]> = {};
    if (body && typeof body === "object")
      for (const [k, v] of Object.entries(body))
        if (Array.isArray(v)) fields[k] = v.map(String);
    throw new ApiError(
      response.status,
      messageFor(response.status, body),
      fields,
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
export const list = <T>(
  resource: string,
  params: Record<string, string | number | undefined> = {},
) => {
  const q = new URLSearchParams();
  Object.entries(params).forEach(
    ([k, v]) => v !== undefined && q.set(k, String(v)),
  );
  return api<Page<T>>(`${resource}${q.size ? `?${q}` : ""}`);
};
export const json = (value: unknown): RequestInit => ({
  body: JSON.stringify(value),
});
