import { apiUrl } from "./base";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parseError(res: Response): Promise<string> {
  const raw = await res.text();
  try {
    const data = JSON.parse(raw);
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join(", ");
    }
  } catch {
    /* HTML from Ingress / Cloudflare */
  }
  if (res.status === 413) {
    return "Fișierul e prea mare pentru Home Assistant. Reîncearcă; pozele se comprimă automat.";
  }
  if (res.status === 502 || res.status === 504 || res.status === 524) {
    return "Home Assistant sau Cloudflare a întrerupt cererea. Reîncearcă; extragerea AI rulează acum în fundal.";
  }
  return res.statusText || `Eroare de rețea (${res.status})`;
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const isForm = options.body instanceof FormData;
  if (!isForm && options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(apiUrl(path), {
    ...options,
    headers,
    credentials: "include",
  });
  if (res.status === 204) return undefined as T;
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  if (res.headers.get("content-type")?.includes("text/csv")) {
    return (await res.text()) as T;
  }
  return (await res.json()) as T;
}
