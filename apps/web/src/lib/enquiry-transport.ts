export class EnquiryTransportError extends Error {
  constructor(public code: string, public status: number) { super(code); }
}

export async function enquiryBody(request: Request): Promise<Record<string, unknown>> {
  if (!/^application\/json(?:\s*;|$)/i.test(request.headers.get("content-type") ?? "")) throw new EnquiryTransportError("invalid_request", 400);
  const reader = request.body?.getReader();
  if (!reader) throw new EnquiryTransportError("invalid_request", 400);
  const chunks: Uint8Array[] = []; let size = 0;
  while (true) {
    const { done, value } = await reader.read(); if (done) break;
    size += value.length;
    if (size > 32768) { await reader.cancel(); throw new EnquiryTransportError("body_too_large", 413); }
    chunks.push(value);
  }
  try {
    const body = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(Buffer.concat(chunks)));
    if (!body || typeof body !== "object" || Array.isArray(body)) throw new Error();
    return body;
  } catch { throw new EnquiryTransportError("invalid_request", 400); }
}
