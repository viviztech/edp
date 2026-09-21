import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { validMutation } from "../../../../lib/bff-security";
import { notificationPath } from "../../../../lib/notification-security";
import { cookieName, csrfName, settings } from "../../../../lib/server-api";

const fail = (code: string, status: number) =>
  NextResponse.json({ error: { code } }, { status, headers: { "Cache-Control": "no-store" } });

async function handle(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  try {
    const config = settings();
    const jar = await cookies();
    const path = notificationPath((await context.params).path, request.method);
    if (!path) return fail("not_found", 404);
    let body: string | undefined;
    if (request.method === "POST") {
      if (!validMutation(request.headers.get("origin"), config.origin, jar.get(csrfName)?.value, request.headers.get("x-csrf-token"))) {
        return fail("csrf_failed", 403);
      }
      if (!request.headers.get("content-type")?.startsWith("application/json")) return fail("invalid_request", 400);
      const reader = request.body?.getReader();
      if (!reader) return fail("invalid_request", 400);
      const chunks: Uint8Array[] = [];
      let size = 0;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        size += value.length;
        if (size > 1024) { await reader.cancel(); return fail("body_too_large", 413); }
        chunks.push(value);
      }
      body = Buffer.concat(chunks).toString("utf8");
      try { JSON.parse(body); } catch { return fail("invalid_request", 400); }
    }
    const query = new URLSearchParams();
    const cursor = request.nextUrl.searchParams.get("cursor");
    if (cursor) {
      if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(cursor)) return fail("invalid_request", 400);
      query.set("cursor", cursor);
    }
    query.set("limit", "25");
    const upstream = await fetch(config.api + "/api/v1" + path + (request.method === "GET" ? `?${query}` : ""), {
      method: request.method, body, cache: "no-store", signal: AbortSignal.timeout(15000),
      headers: {
        "Content-Type": "application/json", "X-BFF-Key": config.key,
        "X-Browser-Session": jar.get(cookieName)?.value ?? "",
        "X-CSRF-Token": request.headers.get("x-csrf-token") ?? "",
      },
    });
    return NextResponse.json(await upstream.json(), {
      status: upstream.status,
      headers: { "Cache-Control": "private, no-store", "X-Robots-Tag": "noindex, nofollow" },
    });
  } catch {
    return fail("service_unavailable", 503);
  }
}
export const GET = handle;
export const POST = handle;
