import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { DELETE, GET, POST } from "./route";

vi.mock("next/headers", () => ({ cookies: async () => ({ get: (name: string) => ({ value: name === "edp_csrf" ? "csrf" : "session" }) }) }));
vi.mock("../../../../lib/server-api", () => ({ cookieName: "edp_session", csrfName: "edp_csrf", settings: () => ({ api: "http://api", key: "server-only-key", origin: "http://localhost:3000" }) }));
const org = "11111111-1111-4111-8111-111111111111";
const item = "22222222-2222-4222-8222-222222222222";
const path = ["organizations", org, "saved", item];
function request(method: string, route = path, body?: string, origin = "http://localhost:3000") {
  return new NextRequest(`http://localhost:3000/api/knowledge/${route.join("/")}`, { method,
    headers: { origin, "content-type": "application/json", "x-csrf-token": "csrf" }, ...(body !== undefined ? { body } : {}) });
}
const context = (value = path) => ({ params: Promise.resolve({ path: value }) });
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });
describe("knowledge BFF transport", () => {
  it("checks route and origin before contacting upstream", async () => {
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    expect((await GET(request("GET", ["..", "auth"]), context(["..", "auth"]))).status).toBe(404);
    expect((await POST(request("POST", path, "{}", "https://unrelated.example"), context())).status).toBe(403);
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("measures UTF-8 bytes, rejects malformed JSON and permits a bounded complete resource", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 })); vi.stubGlobal("fetch", fetchMock);
    const items = ["organizations", org, "items"];
    expect((await POST(request("POST", items, JSON.stringify({ description: "அ".repeat(90000) })), context(items))).status).toBe(413);
    expect((await POST(request("POST", items, "{"), context(items))).status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
    expect((await POST(request("POST", items, JSON.stringify({ description: "அ".repeat(10000) })), context(items))).status).toBe(200);
  });
  it("forwards only validated queries and server credentials, and returns empty DELETE 204", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(new Response("{}", { status: 200 })).mockResolvedValueOnce(new Response(null, { status: 204 })); vi.stubGlobal("fetch", fetchMock);
    const catalog = ["organizations", org, "catalog"];
    const response = await GET(new NextRequest(`http://localhost:3000/api/knowledge/${catalog.join("/")}?locale=ta&kind=funding&limit=25`), context(catalog));
    expect(response.status).toBe(200); expect(response.headers.get("cache-control")).toBe("private, no-store");
    expect(fetchMock.mock.calls[0][0]).toBe(`http://api/api/v1/knowledge/organizations/${org}/catalog?locale=ta&kind=funding&limit=25`);
    expect(fetchMock.mock.calls[0][1].headers["X-Browser-Session"]).toBe("session");
    const deleted = await DELETE(request("DELETE"), context()); expect(deleted.status).toBe(204); expect(await deleted.text()).toBe("");
    expect(deleted.headers.get("set-cookie")).toBeNull();
  });
  it("rejects unrecognized, repeated or mutation query parameters without forwarding", async () => {
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    const catalog = ["organizations", org, "catalog"];
    for (const query of ["token=secret", "locale=en&locale=ta", "limit=1000"]) {
      expect((await GET(new NextRequest(`http://localhost:3000/api/knowledge/${catalog.join("/")}?${query}`), context(catalog))).status).toBe(400);
    }
    expect((await POST(new NextRequest(`http://localhost:3000/api/knowledge/${path.join("/")}?limit=25`, { method: "POST" }), context())).status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
