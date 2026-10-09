import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { validMutation } from "../../../../lib/bff-security";
import { businessPlanPath } from "../../../../lib/business-plan-security";
import { cookieName, csrfName, settings } from "../../../../lib/server-api";

const fail = (code: string, status: number) => NextResponse.json(
  { error: { code } }, { status, headers: { "Cache-Control": "no-store" } },
);

async function handle(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  try {
    const config = settings();
    const jar = await cookies();
    const path = businessPlanPath((await context.params).path, request.method);
    if (!path) return fail("not_found", 404);
    let body: string | undefined;
    if (request.method === "POST") {
      if (!validMutation(request.headers.get("origin"), config.origin, jar.get(csrfName)?.value,
        request.headers.get("x-csrf-token"))) return fail("csrf_failed", 403);
      if (request.headers.get("content-type") &&
          !request.headers.get("content-type")?.startsWith("application/json")) return fail("invalid_request", 400);
      body = await request.text();
      if (body.length > 16384) return fail("body_too_large", 413);
      if (body) { try { JSON.parse(body); } catch { return fail("invalid_request", 400); } }
    }
    const upstream = await fetch(config.api + "/api/v1" + path, {
      method: request.method, body, cache: "no-store", signal: AbortSignal.timeout(15000),
      headers: {
        "X-BFF-Key": config.key,
        "X-Browser-Session": jar.get(cookieName)?.value ?? "",
        "X-CSRF-Token": request.headers.get("x-csrf-token") ?? "",
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      },
    });
    return NextResponse.json(await upstream.json(), {
      status: upstream.status,
      headers: { "Cache-Control": "private, no-store", "X-Robots-Tag": "noindex" },
    });
  } catch { return fail("service_unavailable", 503); }
}

export const GET = handle;
export const POST = handle;
