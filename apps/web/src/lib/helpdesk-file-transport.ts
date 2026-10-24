// This ceiling matches the policy schema; the API also applies the pinned and
// operational limits before it claims an upload or serves verified bytes.
export const helpdeskFileMaxBytes = 104857600;
const suffixes: Record<string, string> = {
  "application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png",
  "image/webp": "webp", "text/plain": "txt",
};
const privateHeaders = {
  "Cache-Control": "private, no-store", "X-Robots-Tag": "noindex, nofollow",
  "X-Content-Type-Options": "nosniff",
};
const fail = (code: string, status: number) => Response.json({ error: { code } }, { status, headers: privateHeaders });

export async function helpdeskFileTransport(request: Request, upstreamUrl: string, credentials: Record<string, string>, documentId: string): Promise<Response> {
  const contentType = request.headers.get("content-type") ?? "";
  const ifMatch = request.headers.get("if-match") ?? "";
  const declared = request.headers.get("content-length");
  let bodyFailure: "body_too_large" | "invalid_request" | null = null;
  let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
  let body: ReadableStream<Uint8Array> | undefined;
  if (request.method === "PUT") {
    if (!Object.hasOwn(suffixes, contentType) || !/^"[1-9][0-9]{0,9}"$/.test(ifMatch) || request.headers.has("content-encoding")) return fail("invalid_request", 400);
    if (declared !== null && !/^[1-9][0-9]*$/.test(declared)) return fail("invalid_request", 400);
    if (declared !== null && (declared.length > 9 || Number(declared) > helpdeskFileMaxBytes)) return fail("body_too_large", 413);
    reader = request.body?.getReader();
    if (!reader) return fail("invalid_request", 400);
    let count = 0;
    body = new ReadableStream<Uint8Array>({
      async pull(controller) {
        try {
          const part = await reader!.read();
          if (part.done) {
            if (!count || (declared !== null && Number(declared) !== count)) {
              bodyFailure = "invalid_request"; controller.error(new Error(bodyFailure));
            } else controller.close();
            return;
          }
          count += part.value.byteLength;
          if (count > helpdeskFileMaxBytes) {
            bodyFailure = "body_too_large"; await reader!.cancel(); controller.error(new Error(bodyFailure)); return;
          }
          controller.enqueue(part.value);
        } catch (error) { controller.error(error); }
      },
      cancel(reason) { return reader!.cancel(reason); },
    });
  }
  try {
    const init: RequestInit & { duplex?: "half" } = {
      method: request.method, cache: "no-store", redirect: "error",
      signal: AbortSignal.any([request.signal, AbortSignal.timeout(100000)]),
      headers: { ...credentials, ...(request.method === "PUT" ? { "Content-Type": contentType, "If-Match": ifMatch } : {}) },
      ...(body ? { body, duplex: "half" } : {}),
    };
    const upstream = await fetch(upstreamUrl, init);
    if (bodyFailure) return fail(bodyFailure, bodyFailure === "body_too_large" ? 413 : 400);
    if (request.method === "PUT" || !upstream.ok) {
      return Response.json(await upstream.json(), { status: upstream.status, headers: privateHeaders });
    }
    const responseType = upstream.headers.get("content-type") ?? "";
    // Starlette appends this charset to its registered text/plain response.
    const media = responseType === "text/plain; charset=utf-8" ? "text/plain" : responseType;
    const length = upstream.headers.get("content-length");
    if (!Object.hasOwn(suffixes, media) || !upstream.body || (length !== null && (!/^[1-9][0-9]*$/.test(length) || length.length > 9 || Number(length) > helpdeskFileMaxBytes))) {
      await upstream.body?.cancel(); return fail("invalid_upstream", 502);
    }
    // The domain API verifies a private snapshot before responding. Keep the BFF
    // response bounded too, and generate its attachment name from the binding ID.
    const source = upstream.body.getReader();
    let count = 0;
    const output = new ReadableStream<Uint8Array>({
      async pull(controller) {
        try {
          const part = await source.read();
          if (part.done) {
            if (!count || (length !== null && Number(length) !== count)) controller.error(new Error("invalid_upstream"));
            else controller.close();
            return;
          }
          count += part.value.byteLength;
          if (count > helpdeskFileMaxBytes) { await source.cancel(); controller.error(new Error("invalid_upstream")); return; }
          controller.enqueue(part.value);
        } catch (error) { controller.error(error); }
      },
      cancel(reason) { return source.cancel(reason); },
    });
    return new Response(output, { status: upstream.status, headers: {
      ...privateHeaders, "Content-Type": responseType,
      "Content-Security-Policy": "sandbox; default-src 'none'",
      "Content-Disposition": `attachment; filename="helpdesk-file-${documentId}.${suffixes[media]}"`,
      ...(length !== null ? { "Content-Length": length } : {}),
    } });
  } catch {
    return fail(bodyFailure ?? "service_unavailable", bodyFailure === "body_too_large" ? 413 : bodyFailure ? 400 : 503);
  } finally {
    // An API rejection can arrive before it consumes the request. Stop reading
    // the browser body in that case, and on timeout/disconnect as well.
    if (reader) await reader.cancel().catch(() => {});
  }
}
