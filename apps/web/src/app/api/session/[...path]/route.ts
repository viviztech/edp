import { randomBytes } from "node:crypto";
import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { backendPath, validMutation } from "../../../../lib/bff-security";
import { cookieName, cookieOptions, csrfName, settings } from "../../../../lib/server-api";

export const runtime = "nodejs";
type Context = { params: Promise<{ path: string[] }> };
function failure(code: string, status: number) {
  return NextResponse.json({ error: { code } }, { status, headers: { "Cache-Control": "no-store" } });
}
async function readBody(request: NextRequest) {
  if (!request.headers.get("content-type")?.startsWith("application/json")) throw new Error("body");
  const reader = request.body?.getReader();
  if (!reader) return "{}";
  const chunks: Uint8Array[] = [];
  let size = 0;
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    size += value.length;
    if (size > 8192) { await reader.cancel(); throw new Error("body"); }
    chunks.push(value);
  }
  const body = Buffer.concat(chunks).toString("utf8");
  JSON.parse(body);
  return body;
}
async function handle(request: NextRequest, context: Context) {
  try {
    const config = settings();
    const jar = await cookies();
    const { path } = await context.params;
    if (request.method === "GET" && path.join("/") === "csrf") {
      const csrf = jar.get(csrfName)?.value ?? randomBytes(32).toString("base64url");
      const response = NextResponse.json({ csrf_token: csrf }, { headers: { "Cache-Control": "no-store" } });
      response.cookies.set(csrfName, csrf, cookieOptions(1209600));
      return response;
    }
    const target = backendPath(path, request.method);
    if (!target) return failure("not_found", 404);
    if (request.method === "POST" && !validMutation(request.headers.get("origin"), config.origin, jar.get(csrfName)?.value, request.headers.get("x-csrf-token"))) return failure("csrf_failed", 403);
    let body: string | undefined;
    if (request.method === "POST") {
      try { body = await readBody(request); } catch { return failure("invalid_request", 400); }
    }
    let suffix = "";
    if (path[0] === "audit") {
      const offset = request.nextUrl.searchParams.get("offset") ?? "0";
      if (!/^\d{1,5}$/.test(offset) || Number(offset) > 10000) return failure("invalid_request", 400);
      suffix = "?offset=" + offset + "&limit=25";
    }
    const upstream = await fetch(config.api + "/api/v1" + target + suffix, {
      method: request.method, body, cache: "no-store", signal: AbortSignal.timeout(10000),
      headers: {
        "Content-Type": "application/json", "X-BFF-Key": config.key,
        "X-Browser-Session": jar.get(cookieName)?.value ?? "",
        "X-CSRF-Token": request.headers.get("x-csrf-token") ?? "",
      },
    });
    const data = await upstream.json();
    if (path[0] === "login" && upstream.ok) {
      const response = NextResponse.json({ status: "signed_in" }, { headers: { "Cache-Control": "no-store" } });
      response.cookies.set(cookieName, data.browser_token, cookieOptions(data.expires_in));
      response.cookies.set(csrfName, data.csrf_token, cookieOptions(data.expires_in));
      return response;
    }
    const response = NextResponse.json(data, { status: upstream.status, headers: { "Cache-Control": "no-store" } });
    if (upstream.headers.get("Retry-After")) response.headers.set("Retry-After", upstream.headers.get("Retry-After")!);
    if ((path[0].startsWith("logout") && upstream.ok) || upstream.status === 401) {
      response.cookies.set(cookieName, "", cookieOptions(0));
      response.cookies.set(csrfName, "", cookieOptions(0));
    }
    return response;
  } catch {
    return failure("service_unavailable", 503);
  }
}
export const GET = handle;
export const POST = handle;
