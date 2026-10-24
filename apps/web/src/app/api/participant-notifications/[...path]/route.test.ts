import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { GET, POST } from "./route";
vi.mock("next/headers", () => ({ cookies: async () => ({ get: (name: string) => ({ value: name === "edp_csrf" ? "csrf" : "server-session" }) }) }));
vi.mock("../../../../lib/server-api", () => ({ cookieName: "edp_session", csrfName: "edp_csrf", settings: () => ({ api: "http://api", key: "server-private-key", origin: "http://localhost:3000" }) }));
const org = "11111111-1111-4111-8111-111111111111", id = "22222222-2222-4222-8222-222222222222";
const root = ["organizations", org], context = (path: string[]) => ({ params: Promise.resolve({ path }) });
const request = (path: string[], body: string, headers: Record<string, string> = {}) => new NextRequest(`http://localhost:3000/api/participant-notifications/${path.join("/")}`, {
  method: "POST", body, headers: { origin: "http://localhost:3000", "content-type": "application/json", "x-csrf-token": "csrf", ...headers },
});
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });
describe("participant inbox BFF", () => {
  it("rejects arbitrary paths, queries, origin and CSRF before forwarding", async () => {
    const mock = vi.fn(); vi.stubGlobal("fetch", mock);
    expect((await GET(new NextRequest("http://localhost:3000/api/participant-notifications/anything"), context(["anything"]))).status).toBe(404);
    for (const query of ["limit=101", "limit=1&limit=2", `recipient_id=${id}`, "topic=enrollment_created"]) expect((await GET(new NextRequest(`http://localhost:3000/api/participant-notifications/${root.join("/")}/mine?${query}`), context([...root, "mine"]))).status).toBe(400);
    expect((await POST(request([...root, "preference"], "{}", { origin: "https://other.example" }), context([...root, "preference"]))).status).toBe(403);
    expect((await POST(request([...root, id, "read"], "{}", { "x-csrf-token": "wrong" }), context([...root, id, "read"]))).status).toBe(403);
    expect(mock).not.toHaveBeenCalled();
  });
  it("bounds UTF-8 JSON bytes, media type and malformed input", async () => {
    const mock = vi.fn(); vi.stubGlobal("fetch", mock); const parts = [...root, "preference"];
    expect((await POST(request(parts, JSON.stringify({ body: "அ".repeat(350) })), context(parts))).status).toBe(413);
    expect((await POST(request(parts, "{"), context(parts))).status).toBe(400);
    expect((await POST(request(parts, "{}", { "content-type": "application/json-malformed" }), context(parts))).status).toBe(400);
    expect(mock).not.toHaveBeenCalled();
  });
  it("forwards exact command/session server credentials without exposing upstream cookies", async () => {
    const mock = vi.fn().mockResolvedValue(Response.json({ enabled: false, topic: "enrollment_created", version: 1 }, { headers: { "set-cookie": "provider=secret", authorization: "secret" } })); vi.stubGlobal("fetch", mock);
    const parts = [...root, "preference"], body = '{"enabled":false,"expected_version":0}';
    const response = await POST(request(parts, body, { "X-BFF-Key": "browser-fake-key" }), context(parts));
    expect(response.status).toBe(200); expect(response.headers.get("cache-control")).toBe("private, no-store");
    expect(response.headers.has("set-cookie")).toBe(false); expect(response.headers.has("authorization")).toBe(false);
    expect(mock.mock.calls[0]).toEqual([`http://api/api/v1/participant-notifications/${parts.join("/")}`, expect.objectContaining({ body, method: "POST", redirect: "error", headers: {
      "Content-Type": "application/json", "X-BFF-Key": "server-private-key", "X-Browser-Session": "server-session", "X-CSRF-Token": "csrf",
    } })]);
  });
  it("preserves bounded pagination and current authorization failures, while reporting upstream failure safely", async () => {
    const mock = vi.fn().mockResolvedValueOnce(Response.json({ error: { code: "forbidden" } }, { status: 403 })).mockRejectedValueOnce(new Error("Private upstream detail")); vi.stubGlobal("fetch", mock);
    const parts = [...root, "mine"], req = () => new NextRequest(`http://localhost:3000/api/participant-notifications/${parts.join("/")}?cursor=${id}&limit=25`);
    expect((await GET(req(), context(parts))).status).toBe(403);
    expect(mock.mock.calls[0][0]).toBe(`http://api/api/v1/participant-notifications/${parts.join("/")}?cursor=${id}&limit=25`);
    const failed = await GET(req(), context(parts)); expect(failed.status).toBe(503); expect(await failed.json()).toEqual({ error: { code: "service_unavailable" } });
  });
});
