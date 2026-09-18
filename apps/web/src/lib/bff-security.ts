import { timingSafeEqual } from "node:crypto";

export function validMutation(origin: string | null, expected: string, csrfCookie: string | undefined, csrfHeader: string | null): boolean {
  if (!origin || origin !== expected || !csrfCookie || !csrfHeader || csrfCookie.length > 128 || csrfHeader.length > 128) return false;
  const a = Buffer.from(csrfCookie), b = Buffer.from(csrfHeader);
  return a.length === b.length && timingSafeEqual(a, b);
}

export function backendPath(path: string[], method: string): string | null {
  const one = path.join("/");
  if (method === "POST" && ["register", "request-verification", "request-reset", "verify", "reset", "logout", "logout-all"].includes(one)) return "/auth/" + one;
  if (method === "POST" && one === "login") return "/auth/browser/login";
  if (method === "GET" && ["me", "sessions"].includes(one)) return "/auth/" + one;
  const id = path[1];
  if (path.length === 2 && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)) {
    if (method === "GET" && path[0] === "staff") return "/system/organizations/" + id + "/access";
    if (method === "GET" && path[0] === "audit") return "/system/organizations/" + id + "/audit";
    if (method === "POST" && path[0] === "revoke") return "/auth/sessions/" + id + "/revoke";
  }
  return null;
}
