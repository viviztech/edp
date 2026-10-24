import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { validMutation } from "../../../../lib/bff-security";
import { helpdeskPath, helpdeskQuery, helpdeskFileContent } from "../../../../lib/helpdesk-security";
import { helpdeskFileTransport } from "../../../../lib/helpdesk-file-transport";
import { cookieName, csrfName, settings } from "../../../../lib/server-api";

const fail = (code: string, status: number) => NextResponse.json({ error: { code } }, {
  status, headers: { "Cache-Control": "no-store" },
});

async function handle(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  try {
    const parts=(await context.params).path;
    const path = helpdeskPath(parts, request.method);
    if (!path) return fail("not_found", 404);
    const query = helpdeskQuery(request.nextUrl.searchParams,parts,request.method);
    if (query === null || request.nextUrl.search.length>1024 || (request.method !== "GET" && query) || (path.includes("/attachments/") && query)) return fail("invalid_request", 400);
    const config = settings(); const jar = await cookies(); let body: string | undefined;
    if(request.method!=="GET" && !validMutation(request.headers.get("origin"),config.origin,jar.get(csrfName)?.value,request.headers.get("x-csrf-token"))) return fail("csrf_failed",403);
    if(helpdeskFileContent(parts)) return helpdeskFileTransport(request,config.api+"/api/v1"+path,{"X-BFF-Key":config.key,"X-Browser-Session":jar.get(cookieName)?.value??"","X-CSRF-Token":request.headers.get("x-csrf-token")??""},parts[5]);
    if (request.method !== "GET") {
      if (!validMutation(request.headers.get("origin"), config.origin, jar.get(csrfName)?.value,
        request.headers.get("x-csrf-token"))) return fail("csrf_failed", 403);
      if (request.headers.get("content-type")?.split(";")[0].trim().toLowerCase()!=="application/json") return fail("invalid_request", 400);
      const reader = request.body?.getReader(); if (!reader) return fail("invalid_request", 400);
      const chunks: Uint8Array[] = []; let size = 0;
      while (true) { const { done, value } = await reader.read(); if (done) break;
        size += value.length; if (size > 262144) { await reader.cancel(); return fail("body_too_large", 413); } chunks.push(value); }
      try { body = new TextDecoder("utf-8", { fatal: true }).decode(Buffer.concat(chunks)); JSON.parse(body); } catch { return fail("invalid_request", 400); }
    }
    const upstream = await fetch(config.api + "/api/v1" + path + (query ? `?${query}` : ""), {
      method: request.method, body, cache: "no-store", signal: AbortSignal.timeout(15000),
      headers: { "X-BFF-Key": config.key, "X-Browser-Session": jar.get(cookieName)?.value ?? "",
        "X-CSRF-Token": request.headers.get("x-csrf-token") ?? "", ...(body !== undefined ? { "Content-Type": "application/json" } : {}) },
    });
    const headers = { "Cache-Control": "private, no-store", "X-Robots-Tag": "noindex, nofollow", "X-Content-Type-Options": "nosniff" };
    if (path.includes("/attachments/") && upstream.ok) {
      const reader = upstream.body?.getReader(); if (!reader) return fail("invalid_response", 502);
      const chunks: Uint8Array[] = []; let size = 0;
      while (true) { const { done, value } = await reader.read(); if (done) break;
        size += value.length; if (size > 32768) { await reader.cancel(); return fail("invalid_response", 502); } chunks.push(value); }
      const bytes = Buffer.concat(chunks);
      const disposition = upstream.headers.get("content-disposition");
      return new NextResponse(bytes, { status: upstream.status, headers: { ...headers,
        "Content-Type": "text/plain; charset=utf-8", "Content-Disposition": disposition?.startsWith("attachment;") ? disposition : "attachment; filename=attachment.txt" } });
    }
    return NextResponse.json(await upstream.json(), { status: upstream.status, headers });
  } catch { return fail("service_unavailable", 503); }
}
export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const DELETE = handle;
