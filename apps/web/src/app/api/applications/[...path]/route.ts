import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { applicationDocumentContent, applicationPath, applicationQuery } from "../../../../lib/application-security";
import { applicationFileTransport } from "../../../../lib/application-file-transport";
import { validMutation } from "../../../../lib/bff-security";
import { cookieName, csrfName, settings } from "../../../../lib/server-api";

const fail = (code: string, status: number) =>
  NextResponse.json({ error: { code } }, { status, headers: { "Cache-Control": "no-store" } });

async function handle(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  try {
    const config = settings();
    const jar = await cookies();
    const segments = (await context.params).path;
    const path = applicationPath(segments, request.method);
    if (!path) return fail("not_found", 404);
    const query = applicationQuery(segments, request.method, request.nextUrl.searchParams);
    if (query === null || request.nextUrl.search.length > 1024) return fail("invalid_request", 400);
    if (request.method !== "GET") {
      if (!validMutation(request.headers.get("origin"), config.origin, jar.get(csrfName)?.value, request.headers.get("x-csrf-token"))) {
        return fail("csrf_failed", 403);
      }
    }
    const credentials = {
      "X-BFF-Key": config.key, "X-Browser-Session": jar.get(cookieName)?.value ?? "",
      "X-CSRF-Token": request.headers.get("x-csrf-token") ?? "",
    };
    if (applicationDocumentContent(segments)) {
      return applicationFileTransport(request, config.api + "/api/v1" + path, credentials, segments[5]);
    }
    let body: string | undefined;
    if (request.method !== "GET") {
      if (!request.headers.get("content-type")?.startsWith("application/json")) return fail("invalid_request", 400);
      const reader = request.body?.getReader();
      if (!reader) return fail("invalid_request", 400);
      const chunks: Uint8Array[] = [];
      let size = 0;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        size += value.length;
        if (size > 262144) { await reader.cancel(); return fail("body_too_large", 413); }
        chunks.push(value);
      }
      try { body = new TextDecoder("utf-8", { fatal: true }).decode(Buffer.concat(chunks)); }
      catch { return fail("invalid_request", 400); }
      try { JSON.parse(body); } catch { return fail("invalid_request", 400); }
    }
    const upstream = await fetch(config.api + "/api/v1" + path + query, {
      method: request.method, body, cache: "no-store", signal: AbortSignal.timeout(15000),
      headers: {
        "Content-Type": "application/json", ...credentials,
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
export const PATCH = handle;
export const PUT = handle;
export const DELETE = handle;
