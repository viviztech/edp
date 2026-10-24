import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { DELETE, GET, PATCH, POST, PUT } from "./route";
import { applicationFileMaxBytes } from "../../../../lib/application-file-transport";

vi.mock("next/headers", () => ({ cookies: async () => ({ get: (name: string) => ({ value: name === "edp_csrf" ? "csrf" : "session" }) }) }));
vi.mock("../../../../lib/server-api", () => ({ cookieName: "edp_session", csrfName: "edp_csrf", settings: () => ({ api: "http://api", key: "server-key", origin: "http://localhost:3000" }) }));
const org = "11111111-1111-4111-8111-111111111111";
const id = "22222222-2222-4222-8222-222222222222";
const context = (path: string[]) => ({ params: Promise.resolve({ path }) });

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("applicant BFF transport", () => {
  it("forwards self-history pagination with only the server-held session and private response headers", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [], next_cursor: null })));
    vi.stubGlobal("fetch", fetchMock);
    const response = await GET(new NextRequest(`http://localhost:3000/api/applications/mine?limit=20&cursor=${id}`), context(["mine"]));
    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    expect(response.headers.get("x-robots-tag")).toContain("noindex");
    expect(fetchMock.mock.calls[0][0]).toBe(`http://api/api/v1/applications/mine?limit=20&cursor=${id}`);
    expect(fetchMock.mock.calls[0][1].headers).toMatchObject({ "X-Browser-Session": "session", "X-BFF-Key": "server-key" });
    expect(JSON.stringify(await response.json())).not.toContain("server-key");
  });

  it("rejects arbitrary scopes, duplicate queries and unsupported writes before contacting the API", async () => {
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    for (const query of ["person_id=other", "limit=20&limit=30", "cursor=../other", "limit=101"]) {
      expect((await GET(new NextRequest(`http://localhost:3000/api/applications/mine?${query}`), context(["mine"]))).status).toBe(400);
    }
    expect((await POST(new NextRequest("http://localhost:3000/api/applications/mine", { method: "POST", body: "{}" }), context(["mine"]))).status).toBe(404);
    expect((await GET(new NextRequest("http://localhost:3000/api/applications/../staff"), context(["..", "staff"]))).status).toBe(404);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("keeps origin, CSRF, UTF-8 and streamed size checks on application writes", async () => {
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    const path = ["organizations", org, "draft", id];
    const make = (body: string | Uint8Array, origin = "http://localhost:3000", csrf = "csrf") => new NextRequest(`http://localhost:3000/api/applications/${path.join("/")}`, {
      method: "PATCH", headers: { origin, "content-type": "application/json", "x-csrf-token": csrf }, body: body as BodyInit,
    });
    expect((await PATCH(make("{}", "https://foreign.example"), context(path))).status).toBe(403);
    expect((await PATCH(make("{}", undefined, "wrong"), context(path))).status).toBe(403);
    expect((await PATCH(make("{"), context(path))).status).toBe(400);
    expect((await PATCH(make(new Uint8Array([0x7b, 0x22, 0x61, 0x22, 0x3a, 0x22, 0xff, 0x22, 0x7d])), context(path))).status).toBe(400);
    expect((await PATCH(make(JSON.stringify({ answer: "அ".repeat(90000) })), context(path))).status).toBe(413);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("streams only an exact scoped PUT with server credentials and a quoted file version", async () => {
    const path = ["organizations", org, "applications", id, "documents", id, "content"];
    const bytes = new TextEncoder().encode("%PDF-1.7 synthetic bytes");
    const forwarded: number[] = [];
    const fetchMock = vi.fn(async (_url: string, init: RequestInit) => {
      const reader = (init.body as ReadableStream<Uint8Array>).getReader();
      while (true) { const part = await reader.read(); if (part.done) break; forwarded.push(...part.value); }
      return Response.json({ application_version: 4, document: { id, file: { version: 5, state: "quarantined" } } });
    });
    vi.stubGlobal("fetch", fetchMock);
    const request = new NextRequest(`http://localhost:3000/api/applications/${path.join("/")}`, {
      method: "PUT", headers: { origin: "http://localhost:3000", "x-csrf-token": "csrf", "content-type": "application/pdf", "if-match": '"3"', "content-length": String(bytes.byteLength), "X-BFF-Key": "browser-attempt", "X-Browser-Session": "browser-attempt" }, body: bytes,
    });
    const response = await PUT(request, context(path));
    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    expect((await response.json()).document.file.state).toBe("quarantined");
    expect(forwarded).toEqual(Array.from(bytes));
    expect(fetchMock.mock.calls[0][1].headers).toEqual({ "X-BFF-Key": "server-key", "X-Browser-Session": "session", "X-CSRF-Token": "csrf", "Content-Type": "application/pdf", "If-Match": '"3"' });
    expect(fetchMock.mock.calls[0][1].headers).not.toHaveProperty("Content-Length");
    expect(fetchMock.mock.calls[0][1].redirect).toBe("error");
    expect(fetchMock.mock.calls[0][0]).toBe(`http://api/api/v1/applications/${path.join("/")}`);
  });

  it("rejects byte encodings, invalid versions, unregistered media and missing origin before forwarding", async () => {
    const path = ["organizations", org, "applications", id, "documents", id, "content"];
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    const headers = { origin: "http://localhost:3000", "x-csrf-token": "csrf", "content-type": "application/pdf", "if-match": '"1"' };
    const invalid: Record<string, string>[] = [{ "content-encoding": "gzip" }, { "if-match": "1" }, { "if-match": 'W/"1"' }, { "content-type": "text/html" }, { "content-type": "application/pdf; charset=utf-8" }, ...["constructor", "toString", "__proto__"].map(value => ({ "content-type": value })), { "content-length": "-1" }, { "content-length": String(applicationFileMaxBytes + 1) }];
    for (const change of invalid) {
      const response = await PUT(new NextRequest(`http://localhost:3000/api/applications/${path.join("/")}`, { method: "PUT", headers: { ...headers, ...change }, body: "x" }), context(path));
      expect([400, 413]).toContain(response.status);
    }
    expect((await PUT(new NextRequest(`http://localhost:3000/api/applications/${path.join("/")}`, { method: "PUT", headers: { ...headers, origin: "https://other.example" }, body: "x" }), context(path))).status).toBe(403);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("counts streamed bytes independently of a missing or misleading Content-Length", async () => {
    const path = ["organizations", org, "applications", id, "documents", id, "content"];
    const headers = { origin: "http://localhost:3000", "x-csrf-token": "csrf", "content-type": "application/pdf", "if-match": '"1"' };
    vi.stubGlobal("fetch", vi.fn(async (_url: string, init: RequestInit) => {
      const reader = (init.body as ReadableStream<Uint8Array>).getReader();
      while (!(await reader.read()).done) { /* Count/discard: never collect a large test body. */ }
      return Response.json({});
    }));
    const mismatch = await PUT(new NextRequest(`http://localhost:3000/api/applications/${path.join("/")}`, { method: "PUT", headers: { ...headers, "content-length": "1" }, body: "two" }), context(path));
    expect(mismatch.status).toBe(400);
    const block = new Uint8Array(1048576);
    for (const declared of [null, "1"]) {
      let sent = 0;
      const body = new ReadableStream({ pull(controller) { controller.enqueue(block); if (++sent === 101) controller.close(); } });
      const init = {
        method: "PUT", headers: { ...headers, ...(declared ? { "content-length": declared } : {}) }, body, duplex: "half" as const,
      };
      const request = new NextRequest(`http://localhost:3000/api/applications/${path.join("/")}`, init);
      const response = await PUT(request, context(path));
      expect(response.status).toBe(413);
      expect(await response.json()).toEqual({ error: { code: "body_too_large" } });
    }
  });

  it("delivers private verified bytes with a binding-based attachment name and strips provider headers", async () => {
    const path = ["organizations", org, "applications", id, "documents", id, "content"];
    const fetchMock = vi.fn().mockResolvedValue(new Response("synthetic text", { headers: { "content-type": "text/plain; charset=utf-8", "content-length": "14", "content-disposition": 'inline; filename="provider-path-secret"', "set-cookie": "leaked=value", "x-storage-key": "private-provider-key" } }));
    vi.stubGlobal("fetch", fetchMock);
    const response = await GET(new NextRequest(`http://localhost:3000/api/applications/${path.join("/")}`), context(path));
    expect(response.status).toBe(200);
    expect(response.headers.get("content-disposition")).toBe(`attachment; filename="application-document-${id}.txt"`);
    expect(response.headers.get("x-content-type-options")).toBe("nosniff");
    expect(response.headers.get("content-type")).toBe("text/plain; charset=utf-8");
    expect(response.headers.get("content-security-policy")).toContain("sandbox");
    expect(response.headers.has("set-cookie")).toBe(false);
    expect(response.headers.has("x-storage-key")).toBe(false);
    expect(fetchMock.mock.calls[0][1].redirect).toBe("error");
    expect(await response.text()).toBe("synthetic text");
  });

  it("keeps document removal as a bounded CSRF-protected JSON command", async () => {
    const path = ["organizations", org, "applications", id, "documents", id];
    const fetchMock = vi.fn().mockResolvedValue(Response.json({ application_version: 5, document: { id, removed_at: "2026-10-23T08:00:00Z" } }));
    vi.stubGlobal("fetch", fetchMock);
    const response = await DELETE(new NextRequest(`http://localhost:3000/api/applications/${path.join("/")}`, { method: "DELETE", headers: { origin: "http://localhost:3000", "x-csrf-token": "csrf", "content-type": "application/json" }, body: JSON.stringify({ expected_version: 4 }) }), context(path));
    expect(response.status).toBe(200);
    expect(fetchMock.mock.calls[0][1].body).toBe('{"expected_version":4}');
  });

  it("rejects inherited-object names as upstream MIME types", async () => {
    const path = ["organizations", org, "applications", id, "documents", id, "content"];
    for (const media of ["constructor", "toString", "__proto__"]) {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("x", { headers: { "content-type": media } })));
      const response = await GET(new NextRequest(`http://localhost:3000/api/applications/${path.join("/")}`), context(path));
      expect(response.status).toBe(502);
      expect(await response.json()).toEqual({ error: { code: "invalid_upstream" } });
    }
  });

  it("cancels an unread upload after an early upstream rejection", async () => {
    const path = ["organizations", org, "applications", id, "documents", id, "content"];
    let cancelled = false;
    const body = new ReadableStream({ pull(controller) { controller.enqueue(new Uint8Array([1])); }, cancel() { cancelled = true; } });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ error: { code: "file_collection_disabled" } }, { status: 503 })));
    const init = { method: "PUT", headers: { origin: "http://localhost:3000", "x-csrf-token": "csrf", "content-type": "application/pdf", "if-match": '"1"' }, body, duplex: "half" as const };
    const response = await PUT(new NextRequest(`http://localhost:3000/api/applications/${path.join("/")}`, init), context(path));
    expect(response.status).toBe(503);
    expect(cancelled).toBe(true);
  });

  it("fails closed if an upstream byte response is truncated or exceeds the delivery ceiling", async () => {
    const path = ["organizations", org, "applications", id, "documents", id, "content"];
    const block = new Uint8Array(1048576);
    for (const oversized of [false, true]) {
      let sent = 0;
      const body = new ReadableStream({ pull(controller) { controller.enqueue(oversized ? block : new Uint8Array([1])); if (++sent === (oversized ? 101 : 1)) controller.close(); } });
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(body, { headers: { "content-type": "application/pdf", ...(!oversized ? { "content-length": "2" } : {}) } })));
      const response = await GET(new NextRequest(`http://localhost:3000/api/applications/${path.join("/")}`), context(path));
      const reader = response.body!.getReader();
      async function consume() { while (!(await reader.read()).done) { /* Discard bounded chunks. */ } }
      await expect(consume()).rejects.toThrow("invalid_upstream");
    }
  });
});
