export class DocumentRequestError extends Error {
  constructor(public status: number, public code: string) { super(code); }
}

export async function documentRequest<T>(path: string, method = "GET", data?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  if (method !== "GET") {
    const token = await fetch("/api/session/csrf", { cache: "no-store" });
    if (!token.ok) throw new DocumentRequestError(token.status, "csrf_unavailable");
    headers["x-csrf-token"] = (await token.json()).csrf_token;
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(path, { method, headers, cache: "no-store", ...(data === undefined ? {} : { body: JSON.stringify(data) }) });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new DocumentRequestError(response.status, result?.error?.code ?? "request_failed");
  return result as T;
}

export async function prepareApplicationFile<Media extends string>(file: File, allowed: readonly Media[], maxBytes: number) {
  const media = allowed.find(value => value === file.type);
  if (!Number.isInteger(maxBytes) || maxBytes < 1 || file.size < 1 || file.size > maxBytes || !media) throw new Error("invalid_file");
  const bytes = await file.arrayBuffer();
  if (bytes.byteLength !== file.size || bytes.byteLength > maxBytes) throw new Error("invalid_file");
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return { media_type: media, byte_size: file.size, sha256: Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, "0")).join("") };
}

export async function uploadApplicationFile<T>(path: string, file: File, version: number): Promise<T> {
  if (!Number.isInteger(version) || version < 1) throw new Error("invalid_version");
  const token = await fetch("/api/session/csrf", { cache: "no-store" });
  if (!token.ok) throw new DocumentRequestError(token.status, "csrf_unavailable");
  const response = await fetch(path, { method: "PUT", headers: {
    "x-csrf-token": (await token.json()).csrf_token, "Content-Type": file.type, "If-Match": `"${version}"`,
  }, body: file, cache: "no-store" });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new DocumentRequestError(response.status, result?.error?.code ?? "request_failed");
  return result as T;
}
