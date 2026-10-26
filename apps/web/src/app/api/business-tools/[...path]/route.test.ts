import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { GET, POST } from "./route";
vi.mock("next/headers", () => ({ cookies: async () => ({ get: (name: string) => ({ value: name === "edp_csrf" ? "csrf" : "session" }) }) }));
vi.mock("../../../../lib/server-api", () => ({ cookieName: "edp_session", csrfName: "edp_csrf", settings: () => ({ api: "http://api", key: "server-key", origin: "http://localhost:3000" }) }));
const org = "11111111-1111-4111-8111-111111111111";
const profile = "22222222-2222-4222-8222-222222222222";
const base = ["organizations", org, "profiles", profile];
const context = (tail: string[]) => ({ params: Promise.resolve({ path: [...base, ...tail] }) });
const request = (tail: string, body: string, origin = "http://localhost:3000") => new NextRequest(`http://localhost:3000/api/business-tools/${[...base, tail].join("/")}`, {
  method: "POST", headers: { origin, "content-type": "application/json", "x-csrf-token": "csrf" }, body,
});
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });
describe("business tools BFF", () => {
  it("rejects unknown routes, methods and unsupported owner/query overrides", async () => {
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    expect((await GET(new NextRequest("http://localhost:3000/api/business-tools/x"), context(["customers", "export"])) ).status).toBe(404);
    for (const query of ["owner=other", "limit=500", "offset=10001", "status=all", "limit=1&limit=2"]) {
      expect((await GET(new NextRequest(`http://localhost:3000/api/business-tools/tasks?${query}`), context(["tasks"]))).status).toBe(400);
    }
    expect((await POST(request("card", "{}", "https://unrelated.example"), context(["card"]))).status).toBe(403);
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("bounds actual UTF-8 bytes and rejects malformed JSON", async () => {
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    expect((await POST(request("card", JSON.stringify({ text: "அ".repeat(44000) })), context(["card"]))).status).toBe(413);
    expect((await POST(request("card", "{"), context(["card"]))).status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("forwards exact decimal request bodies and only validated task filters with private caching", async () => {
    const fetchMock = vi.fn().mockImplementation(async () => new Response("{}")); vi.stubGlobal("fetch", fetchMock);
    const body = JSON.stringify({ unit_price: "0.10", quantity: "1.005" });
    const result = await POST(request("quotes", body), context(["quotes"]));
    expect(result.status).toBe(200); expect(result.headers.get("cache-control")).toContain("no-store");
    expect(fetchMock.mock.calls[0][1].body).toBe(body);
    expect(fetchMock.mock.calls[0][1].headers["X-Browser-Session"]).toBe("session");
    await GET(new NextRequest(`http://localhost:3000/api/business-tools/tasks?contact_id=${profile}&status=pending&limit=25&offset=0`), context(["tasks"]));
    expect(fetchMock.mock.calls[1][0]).toContain(`contact_id=${profile}&status=pending`);
    await GET(new NextRequest("http://localhost:3000/api/business-tools/contacts?status=customer&search=Name%20%26%20Company"), context(["contacts"]));
    expect(fetchMock.mock.calls[2][0]).toContain("search=Name+%26+Company");
  });
  it("returns printable HTML as a script-free sandboxed attachment and preserves denial", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(new Response("<!doctype html><p>Quotation</p>"))
      .mockResolvedValueOnce(Response.json({ error: { code: "forbidden" } }, { status: 403 })); vi.stubGlobal("fetch", fetchMock);
    const result = await GET(new NextRequest("http://localhost:3000/api/business-tools/card/artifact"), context(["card", "artifact"]));
    expect(result.headers.get("content-disposition")).toContain("attachment;");
    expect(result.headers.get("content-security-policy")).toContain("sandbox;");
    expect(result.headers.get("content-security-policy")).not.toContain("allow-scripts");
    expect((await GET(new NextRequest("http://localhost:3000/api/business-tools/card/artifact"), context(["card", "artifact"]))).status).toBe(403);
  });
});
