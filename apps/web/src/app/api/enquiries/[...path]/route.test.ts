import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { GET, POST } from "./route";
vi.mock("next/headers", () => ({ cookies: async () => ({ get: (name: string) => ({ value: name === "edp_csrf" ? "csrf" : "session" }) }) }));
vi.mock("../../../../lib/server-api", () => ({ cookieName: "edp_session", csrfName: "edp_csrf", settings: () => ({ api: "http://api", key: "server-key", origin: "http://localhost:3000" }) }));
const org = "11111111-1111-4111-8111-111111111111", id = "22222222-2222-4222-8222-222222222222";
const path = ["organizations", org, "enquiries", id, "status"], queue = ["organizations", org, "enquiries", "queue"];
const context = (path: string[]) => ({ params: Promise.resolve({ path }) });
function request(method: string, parts = path, query = "", body?: BodyInit, origin = "http://localhost:3000") {
  return new NextRequest(`http://localhost:3000/api/enquiries/${parts.join("/")}${query}`, { method, ...(body ? { body } : {}), headers: { origin, "content-type": "application/json", "x-csrf-token": "csrf" } });
}
afterEach(() => { vi.unstubAllGlobals(); });
describe("staff enquiry proxy", () => {
  it("blocks unsupported paths/queries and cross-origin commands before upstream", async () => {
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    expect((await GET(request("GET", ["auth", "me"]), context(["auth", "me"]))).status).toBe(404);
    expect((await GET(request("GET", queue, "?status=new&status=closed"), context(queue))).status).toBe(400);
    expect((await POST(request("POST", path, "?limit=1", "{}"), context(path))).status).toBe(400);
    expect((await POST(request("POST", path, "", "{}", "https://evil.test"), context(path))).status).toBe(403);
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("forwards scoped queue filters and server session with private cache controls", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [], next_cursor: null }))); vi.stubGlobal("fetch", fetchMock);
    const response = await GET(request("GET", queue, "?limit=25&status=new"), context(queue));
    expect(fetchMock.mock.calls[0][0]).toBe(`http://api/api/v1/cms/organizations/${org}/enquiries/queue?limit=25&status=new`);
    expect(fetchMock.mock.calls[0][1].headers["X-Browser-Session"]).toBe("session"); expect(response.headers.get("cache-control")).toBe("private, no-store");
  });
  it("rejects oversized or malformed mutation bytes and preserves conflict status", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code: "version_conflict" } }), { status: 409 })); vi.stubGlobal("fetch", fetchMock);
    expect((await POST(request("POST", path, "", "x".repeat(32769)), context(path))).status).toBe(413);
    expect((await POST(request("POST", path, "", new Uint8Array([0xff])), context(path))).status).toBe(400);
    const response = await POST(request("POST", path, "", JSON.stringify({ status: "reviewed", expected_version: 1 })), context(path));
    expect(response.status).toBe(409); expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
