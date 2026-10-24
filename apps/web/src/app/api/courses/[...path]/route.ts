import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { validMutation } from "../../../../lib/bff-security";
import { learningPath, learningQuery } from "../../../../lib/learning-security";
import { applicationFileTransport } from "../../../../lib/application-file-transport";
import { cookieName, csrfName, settings } from "../../../../lib/server-api";

const fail = (code: string, status: number) => NextResponse.json(
  { error: { code } },
  { status, headers: { "Cache-Control": "no-store" } },
);

function upstreamResponse(upstream: Response) {
  const contentType = upstream.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return upstream.json().then((body) => NextResponse.json(body, {
      status: upstream.status,
      headers: {
        "Cache-Control": "private, no-store",
        "X-Robots-Tag": "noindex, nofollow",
      },
    }));
  }
  const headers = new Headers({
    "Cache-Control": "private, no-store",
    "X-Content-Type-Options": "nosniff",
    "X-Robots-Tag": "noindex, nofollow",
    "Content-Security-Policy": "sandbox; default-src 'none'",
  });
  for (const name of ["content-type", "content-length", "content-disposition", "accept-ranges"]) {
    const value = upstream.headers.get(name);
    if (value) headers.set(name, value);
  }
  return Promise.resolve(new Response(upstream.body, { status: upstream.status, headers }));
}

async function handle(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  try {
    const config = settings();
    const jar = await cookies();
    const path = learningPath((await context.params).path, request.method);
    if (!path || !learningQuery(path, request.nextUrl.searchParams)) return fail("not_found", 404);
    const headers: Record<string, string> = {
      "X-BFF-Key": config.key,
      "X-Browser-Session": jar.get(cookieName)?.value ?? "",
      "X-CSRF-Token": request.headers.get("x-csrf-token") ?? "",
    };
    const byteRoute = path.endsWith("/content");
    let body: string | undefined;
    if (request.method !== "GET") {
      if (!validMutation(
        request.headers.get("origin"),
        config.origin,
        jar.get(csrfName)?.value,
        request.headers.get("x-csrf-token"),
      )) return fail("csrf_failed", 403);
      if (byteRoute && request.method === "PUT") {
        return applicationFileTransport(request, config.api + "/api/v1" + path, headers,
          path.split("/").at(-2)!, "learning-file");
      }
      if (request.headers.get("content-type") &&
          !request.headers.get("content-type")?.startsWith("application/json")) {
        return fail("invalid_request", 400);
      }
      if (request.body) {
        const reader = request.body.getReader();
        const chunks: Uint8Array[] = [];
        let size = 0;
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          size += value.length;
          if (size > 65536) {
            await reader.cancel();
            return fail("body_too_large", 413);
          }
          chunks.push(value);
        }
        try { body = new TextDecoder("utf-8", { fatal: true }).decode(Buffer.concat(chunks)); }
        catch { return fail("invalid_request", 400); }
        if (body) {
          try { JSON.parse(body); } catch { return fail("invalid_request", 400); }
        }
      }
    }
    if (byteRoute && request.method === "GET") {
      return applicationFileTransport(request, config.api + "/api/v1" + path, headers,
        path.split("/").at(-2)!, "learning-file");
    }
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const upstream = await fetch(config.api + "/api/v1" + path + request.nextUrl.search, {
      method: request.method,
      redirect: "error",
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(15000),
      headers,
    });
    return await upstreamResponse(upstream);
  } catch {
    return fail("service_unavailable", 503);
  }
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const DELETE = handle;
