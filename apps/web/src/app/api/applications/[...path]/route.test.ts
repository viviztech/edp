import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { GET, PATCH, POST } from "./route";

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
});
