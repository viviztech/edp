import "server-only";
import { cookies } from "next/headers";

export function settings() {
  const api = process.env.API_INTERNAL_URL;
  const key = process.env.BFF_KEY;
  const origin = process.env.WEB_ORIGIN;
  if (!api || !key || key.length < 32 || !origin) throw new Error("Server configuration missing");
  const url = new URL(origin);
  const local = ["localhost", "127.0.0.1"].includes(url.hostname);
  const secure = process.env.COOKIE_SECURE === "true";
  if (url.origin !== origin || (!local && (url.protocol !== "https:" || !secure))) throw new Error("Secure origin required");
  return { api: api.replace(/\/$/, ""), key, origin, secure };
}

export const cookieName = "edp_session";
export const csrfName = "edp_csrf";
export function cookieOptions(maxAge: number) {
  return { httpOnly: true, secure: settings().secure, sameSite: "strict" as const, path: "/", maxAge };
}

export async function serverApi(path: string) {
  const config = settings();
  const jar = await cookies();
  return fetch(config.api + "/api/v1" + path, {
    headers: { "X-BFF-Key": config.key, "X-Browser-Session": jar.get(cookieName)?.value ?? "" },
    cache: "no-store", signal: AbortSignal.timeout(8000),
  });
}
