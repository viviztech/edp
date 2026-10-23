import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { validMutation } from "../../../../lib/bff-security";
import { filePolicyPath, filePolicyQuery } from "../../../../lib/file-policy-security";
import { cookieName, csrfName, settings } from "../../../../lib/server-api";

const privateHeaders = { "Cache-Control": "private, no-store", "X-Robots-Tag": "noindex, nofollow", "X-Content-Type-Options": "nosniff" };
const fail = (code: string, status: number) => NextResponse.json({ error: { code } }, { status, headers: privateHeaders });
async function handle(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  try {
    const parts = (await context.params).path;
    const path = filePolicyPath(parts, request.method);
    if (!path) return fail("not_found", 404);
    const query = filePolicyQuery(parts, request.method, request.nextUrl.searchParams);
    if (query === null) return fail("invalid_request", 400);
    const config = settings(); const jar = await cookies(); let body: string | undefined;
    if (request.method !== "GET") {
      if (!validMutation(request.headers.get("origin"), config.origin, jar.get(csrfName)?.value, request.headers.get("x-csrf-token"))) return fail("csrf_failed", 403);
      if (request.headers.get("content-type")?.split(";")[0].trim().toLowerCase() !== "application/json") return fail("invalid_request", 400);
      const reader = request.body?.getReader(); if (!reader) return fail("invalid_request", 400);
      const chunks: Uint8Array[] = []; let size = 0;
      while (true) {
        const { done, value } = await reader.read(); if (done) break;
        size += value.length; if (size > 65536) { await reader.cancel(); return fail("body_too_large", 413); } chunks.push(value);
      }
      try {
        body = new TextDecoder("utf-8", { fatal: true }).decode(Buffer.concat(chunks));
        const value = JSON.parse(body);
        if (!value || typeof value !== "object" || Array.isArray(value)) return fail("invalid_request", 400);
      } catch { return fail("invalid_request", 400); }
    }
    const upstream = await fetch(config.api + "/api/v1" + path + (query ? `?${query}` : ""), {
      method: request.method, body, cache: "no-store", signal: AbortSignal.timeout(10000),
      headers: { "X-BFF-Key": config.key, "X-Browser-Session": jar.get(cookieName)?.value ?? "",
        "X-CSRF-Token": request.headers.get("x-csrf-token") ?? "", ...(body ? { "Content-Type": "application/json" } : {}) },
    });
    return NextResponse.json(await upstream.json(), { status: upstream.status, headers: privateHeaders });
  } catch { return fail("service_unavailable", 503); }
}
export const GET = handle;
export const POST = handle;
export const PATCH = handle;
