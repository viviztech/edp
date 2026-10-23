import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { validMutation } from "../../../../lib/bff-security";
import { knowledgePath, knowledgeQuery } from "../../../../lib/knowledge-security";
import { cookieName, csrfName, settings } from "../../../../lib/server-api";

const fail = (code: string, status: number) => NextResponse.json({ error: { code } }, {
  status, headers: { "Cache-Control": "no-store" },
});

async function handle(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  try {
    const path = knowledgePath((await context.params).path, request.method);
    if (!path) return fail("not_found", 404);
    const query = knowledgeQuery(request.nextUrl.searchParams);
    if (query === null || (request.method !== "GET" && query)) return fail("invalid_request", 400);
    const config = settings();
    const jar = await cookies();
    let body: string | undefined;
    if (request.method !== "GET") {
      if (!validMutation(request.headers.get("origin"), config.origin, jar.get(csrfName)?.value,
        request.headers.get("x-csrf-token"))) return fail("csrf_failed", 403);
      if (request.method !== "DELETE") {
        if (!request.headers.get("content-type")?.startsWith("application/json")) return fail("invalid_request", 400);
        const reader = request.body?.getReader();
        if (!reader) return fail("invalid_request", 400);
        const chunks: Uint8Array[] = []; let size = 0;
        while (true) {
          const { done, value } = await reader.read(); if (done) break;
          size += value.length;
          if (size > 262144) { await reader.cancel(); return fail("body_too_large", 413); }
          chunks.push(value);
        }
        body = Buffer.concat(chunks).toString("utf8");
        try { JSON.parse(body); } catch { return fail("invalid_request", 400); }
      }
    }
    const upstream = await fetch(config.api + "/api/v1" + path + (query ? `?${query}` : ""), {
      method: request.method, body, cache: "no-store", signal: AbortSignal.timeout(15000),
      headers: { "X-BFF-Key": config.key, "X-Browser-Session": jar.get(cookieName)?.value ?? "",
        "X-CSRF-Token": request.headers.get("x-csrf-token") ?? "",
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}) },
    });
    const headers = { "Cache-Control": "private, no-store", "X-Robots-Tag": "noindex, nofollow" };
    if (upstream.status === 204) return new NextResponse(null, { status: 204, headers });
    return NextResponse.json(await upstream.json(), { status: upstream.status, headers });
  } catch { return fail("service_unavailable", 503); }
}

export const GET = handle;
export const POST = handle;
export const PATCH = handle;
export const DELETE = handle;
