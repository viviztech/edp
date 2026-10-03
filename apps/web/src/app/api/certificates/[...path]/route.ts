import { NextRequest, NextResponse } from "next/server";
import { certificatePath } from "../../../../lib/certificate-security";
import { settings } from "../../../../lib/server-api";

const fail = (code: string, status: number) => NextResponse.json(
  { error: { code } },
  { status, headers: { "Cache-Control": "no-store" } },
);

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  try {
    const config = settings();
    const path = certificatePath((await context.params).path, request.method);
    if (!path) return fail("not_found", 404);
    const response = await fetch(config.api + "/api/v1" + path, {
      cache: "no-store",
      signal: AbortSignal.timeout(8000),
      headers: { "X-BFF-Key": config.key },
    });
    const contentType = response.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      return NextResponse.json(await response.json(), {
        status: response.status,
        headers: { "Cache-Control": "no-store" },
      });
    }
    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "public, max-age=300",
        "X-Content-Type-Options": "nosniff",
      },
    });
  } catch {
    return fail("service_unavailable", 503);
  }
}
