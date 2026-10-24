import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { validMutation } from "../../../../lib/bff-security";
import { participantNotificationPath, participantNotificationQuery } from "../../../../lib/participant-notification-security";
import { cookieName, csrfName, settings } from "../../../../lib/server-api";

const responseHeaders = { "Cache-Control": "private, no-store", "X-Robots-Tag": "noindex, nofollow" };
const fail = (code: string, status: number) => NextResponse.json({ error: { code } }, { status, headers: responseHeaders });
async function handle(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  try {
    const path = participantNotificationPath((await context.params).path, request.method);
    if (!path) return fail("not_found", 404);
    const query = participantNotificationQuery(path, request.method, request.nextUrl.searchParams);
    if (query === null) return fail("invalid_request", 400);
    const config = settings(), jar = await cookies();
    let body: string | undefined;
    if (request.method === "POST") {
      if (!validMutation(request.headers.get("origin"), config.origin, jar.get(csrfName)?.value, request.headers.get("x-csrf-token"))) return fail("csrf_failed", 403);
      if (!/^application\/json(?:\s*;|$)/i.test(request.headers.get("content-type") ?? "")) return fail("invalid_request", 400);
      const reader = request.body?.getReader();
      if (!reader) return fail("invalid_request", 400);
      const chunks: Uint8Array[] = []; let size = 0;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        size += value.length;
        if (size > 1024) { await reader.cancel(); return fail("body_too_large", 413); }
        chunks.push(value);
      }
      try { body = new TextDecoder("utf-8", { fatal: true }).decode(Buffer.concat(chunks)); JSON.parse(body); }
      catch { return fail("invalid_request", 400); }
    }
    const upstream = await fetch(config.api + "/api/v1" + path + (query ? `?${query}` : ""), {
      method: request.method, body, cache: "no-store", redirect: "error", signal: AbortSignal.timeout(10000),
      headers: { "Content-Type": "application/json", "X-BFF-Key": config.key, "X-Browser-Session": jar.get(cookieName)?.value ?? "", "X-CSRF-Token": request.headers.get("x-csrf-token") ?? "" },
    });
    return NextResponse.json(await upstream.json(), { status: upstream.status, headers: responseHeaders });
  } catch { return fail("service_unavailable", 503); }
}
export const GET = handle;
export const POST = handle;
