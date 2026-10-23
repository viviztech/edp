import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { GET, PATCH, POST } from "./route";
vi.mock("next/headers", () => ({ cookies: async () => ({ get: (name: string) => ({ value: name === "edp_csrf" ? "csrf" : "session" }) }) }));
vi.mock("../../../../lib/server-api", () => ({ cookieName: "edp_session", csrfName: "edp_csrf", settings: () => ({ api: "http://api", key: "private-policy-key", origin: "http://localhost:3000" }) }));
const org = "11111111-1111-4111-8111-111111111111", id = "22222222-2222-4222-8222-222222222222";
const parts = ["organizations", org, "policies"];
const context = (path = parts) => ({ params: Promise.resolve({ path }) });
function request(method = "GET", path = parts, query = "", body?: BodyInit, origin = "http://localhost:3000") {
  return new NextRequest(`http://localhost:3000/api/file-policies/${path.join("/")}${query}`, { method, ...(body !== undefined ? { body } : {}), headers: { origin, "x-csrf-token": "csrf", "content-type": "application/json" } });
}
afterEach(() => { vi.unstubAllGlobals(); });
describe("file-policy BFF", () => {
  it("rejects byte/activation routes, unknown filters and cross-origin writes before upstream", async () => {
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    const bytes = ["organizations", org, "files", id, "download"];
    expect((await GET(request("GET", bytes), context(bytes))).status).toBe(404);
    expect((await POST(request("POST", [...parts, id, "activate"], "", "{}"), context([...parts, id, "activate"]))).status).toBe(404);
    expect((await GET(request("GET", parts, "?purpose=cms_asset&purpose=lms_material"), context())).status).toBe(400);
    expect((await POST(request("POST", parts, "", "{}", "https://unrelated.example"), context())).status).toBe(403);
    expect((await PATCH(request("PATCH", [...parts, id], "?limit=1", "{}"), context([...parts, id]))).status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("counts actual UTF-8 bytes and rejects malformed encoding or JSON before forwarding", async () => {
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    expect((await POST(request("POST", parts, "", JSON.stringify({ notice_ta: "த".repeat(22000) })), context())).status).toBe(413);
    expect((await POST(request("POST", parts, "", new Uint8Array([123, 34, 120, 34, 58, 34, 255, 34, 125])), context())).status).toBe(400);
    for (const body of ["{", "[]", "null"]) expect((await POST(request("POST", parts, "", body), context())).status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("supports complete bilingual notices and preserves permission/version results without credential leakage", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ items: [], next_cursor: null }), { headers: { "set-cookie": "private=hidden" } }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ error: { code: "version_conflict" } }), { status: 409 })); vi.stubGlobal("fetch", fetchMock);
    const response = await GET(request("GET", parts, `?purpose=cms_asset&cursor=${id}`), context());
    expect(fetchMock.mock.calls[0][0]).toBe(`http://api/api/v1/files/organizations/${org}/policies?purpose=cms_asset&cursor=${id}&limit=25`);
    expect(response.headers.get("cache-control")).toBe("private, no-store"); expect(response.headers.get("set-cookie")).toBeNull();
    expect(fetchMock.mock.calls[0][1].headers).toMatchObject({ "X-BFF-Key": "private-policy-key", "X-Browser-Session": "session" });
    const body = JSON.stringify({ notice_en: "த".repeat(4000), notice_ta: "த".repeat(4000), expected_version: 1 });
    const edited = await PATCH(request("PATCH", [...parts, id], "", body), context([...parts, id]));
    expect(edited.status).toBe(409); expect(fetchMock.mock.calls[1][1].body).toBe(body);
    expect(await edited.json()).toEqual({ error: { code: "version_conflict" } });
  });
});
