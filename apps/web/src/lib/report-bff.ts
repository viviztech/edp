import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { validMutation } from "./bff-security";
import { cookieName, csrfName, settings } from "./server-api";

const fail = (code: string, status: number) => NextResponse.json({ error: { code } }, {
  status, headers: { "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff" },
});

export function reportBff(pathCheck: (path: string[], method: string) => string | null,
  queryCheck: (query: URLSearchParams) => string | null) {
  return async function handle(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
    try {
      const path = pathCheck((await context.params).path, request.method);
      if (!path) return fail("not_found", 404);
      const query = queryCheck(request.nextUrl.searchParams);
      if (query === null || (request.method !== "GET" && query) || (path.includes("/download/") && query)) return fail("invalid_request", 400);
      const config = settings(); const jar = await cookies(); let body: string | undefined;
      if (request.method !== "GET") {
        if (!validMutation(request.headers.get("origin"), config.origin, jar.get(csrfName)?.value,
          request.headers.get("x-csrf-token"))) return fail("csrf_failed", 403);
        if (!/^application\/json(?:\s*;|$)/i.test(request.headers.get("content-type") ?? "")) return fail("invalid_request", 400);
        const reader = request.body?.getReader(); if (!reader) return fail("invalid_request", 400);
        const chunks: Uint8Array[] = []; let size = 0;
        while (true) {
          const { done, value } = await reader.read(); if (done) break;
          size += value.length; if (size > 65536) { await reader.cancel(); return fail("body_too_large", 413); }
          chunks.push(value);
        }
        try { body = new TextDecoder("utf-8", { fatal: true }).decode(Buffer.concat(chunks)); JSON.parse(body); }
        catch { return fail("invalid_request", 400); }
      }
      const upstream = await fetch(`${config.api}/api/v1${path}${query ? `?${query}` : ""}`, {
        method: request.method, body, cache: "no-store", signal: AbortSignal.timeout(30000),
        headers: { "X-BFF-Key": config.key, "X-Browser-Session": jar.get(cookieName)?.value ?? "",
          "X-CSRF-Token": request.headers.get("x-csrf-token") ?? "", ...(body !== undefined ? { "Content-Type": "application/json" } : {}) },
      });
      const headers = { "Cache-Control": "private, no-store", "X-Robots-Tag": "noindex, nofollow", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer" };
      if (path.includes("/download/") && upstream.ok) {
        if (!upstream.headers.get("content-type")?.startsWith("text/csv")) return fail("invalid_response", 502);
        const reader = upstream.body?.getReader(); if (!reader) return fail("invalid_response", 502);
        const chunks: Uint8Array[] = []; let size = 0;
        while (true) {
          const { done, value } = await reader.read(); if (done) break;
          size += value.length; if (size > 262144) { await reader.cancel(); return fail("invalid_response", 502); }
          chunks.push(value);
        }
        return new NextResponse(Buffer.concat(chunks), { status: upstream.status,
          headers: { ...headers, "Content-Type": "text/csv; charset=utf-8", "Content-Disposition": 'attachment; filename="impact-report.csv"' } });
      }
      return NextResponse.json(await upstream.json(), { status: upstream.status, headers });
    } catch { return fail("service_unavailable", 503); }
  };
}
