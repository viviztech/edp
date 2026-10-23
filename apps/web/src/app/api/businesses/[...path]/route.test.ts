import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { GET, POST } from "./route";

vi.mock("next/headers", () => ({ cookies: async () => ({ get: (name: string) => ({ value: name === "edp_csrf" ? "csrf" : "session" }) }) }));
vi.mock("../../../../lib/server-api", () => ({ cookieName: "edp_session", csrfName: "edp_csrf", settings: () => ({ api: "http://api", key: "server-key", origin: "http://localhost:3000" }) }));
const org = "11111111-1111-4111-8111-111111111111";
const path = ["organizations", org, "profiles"];
const context = (route = path) => ({ params: Promise.resolve({ path: route }) });
const request = (body: string, origin = "http://localhost:3000") => new NextRequest(`http://localhost:3000/api/businesses/${path.join("/")}`, {
  method: "POST", headers: { origin, "content-type": "application/json", "x-csrf-token": "csrf" }, body,
});
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });
describe("business tracking BFF", () => {
  it("rejects invalid routes, query overrides and foreign-origin writes before forwarding", async () => {
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    expect((await GET(new NextRequest("http://localhost:3000/api/businesses/anything"), context(["anything"]))).status).toBe(404);
    const mine = ["organizations", org, "mine"];
    expect((await GET(new NextRequest(`http://localhost:3000/api/businesses/${mine.join("/")}?owner=other`), context(mine))).status).toBe(400);
    expect((await POST(request("{}", "https://other.example"), context())).status).toBe(403);
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("bounds streamed UTF-8 bytes while accepting a full Tamil outcome", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(new Response("{}"))); vi.stubGlobal("fetch", fetchMock);
    expect((await POST(request(JSON.stringify({ text: "அ".repeat(22000) })), context())).status).toBe(413);
    expect((await POST(request("{"), context())).status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
    expect((await POST(request(JSON.stringify({ challenges: "அ".repeat(4000), outcomes: "ஆ".repeat(4000) })), context())).status).toBe(200);
    expect(fetchMock.mock.calls[0][1].headers["X-Browser-Session"]).toBe("session");
  });
});
