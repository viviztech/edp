import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { validMutation } from "../../../../lib/bff-security";
import { enquiryPath, enquiryQuery } from "../../../../lib/enquiry-security";
import { enquiryBody, EnquiryTransportError } from "../../../../lib/enquiry-transport";
import { cookieName, csrfName, settings } from "../../../../lib/server-api";

const headers = { "Cache-Control": "private, no-store", "X-Robots-Tag": "noindex, nofollow", "X-Content-Type-Options": "nosniff" };
const fail = (code: string, status: number) => NextResponse.json({ error: { code } }, { status, headers });
async function handle(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  try {
    const path = enquiryPath((await context.params).path, request.method);
    if (!path) return fail("not_found", 404);
    const query = enquiryQuery(request.nextUrl.searchParams, path, request.method);
    if (query === null) return fail("invalid_request", 400);
    const config = settings(); const jar = await cookies(); let body: string | undefined;
    if (request.method === "POST") {
      if (!validMutation(request.headers.get("origin"), config.origin, jar.get(csrfName)?.value, request.headers.get("x-csrf-token"))) return fail("csrf_failed", 403);
      body = JSON.stringify(await enquiryBody(request));
    }
    const upstream = await fetch(config.api + "/api/v1" + path + (query ? `?${query}` : ""), {
      method: request.method, body, cache: "no-store", signal: AbortSignal.timeout(10000),
      headers: { "X-BFF-Key": config.key, "X-Browser-Session": jar.get(cookieName)?.value ?? "",
        "X-CSRF-Token": request.headers.get("x-csrf-token") ?? "", ...(body ? { "Content-Type": "application/json" } : {}) },
    });
    return NextResponse.json(await upstream.json(), { status: upstream.status, headers });
  } catch (error) {
    return error instanceof EnquiryTransportError ? fail(error.code, error.status) : fail("service_unavailable", 503);
  }
}
export const GET = handle;
export const POST = handle;
