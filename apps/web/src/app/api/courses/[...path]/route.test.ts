import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { DELETE, GET, POST, PUT } from "./route";

vi.mock("next/headers", () => ({ cookies: async () => ({ get: (name: string) => ({ value: name === "edp_csrf" ? "csrf" : "session" }) }) }));
vi.mock("../../../../lib/server-api", () => ({ cookieName: "edp_session", csrfName: "edp_csrf", settings: () => ({ api: "http://api", key: "server-key", origin: "http://localhost:3000" }) }));
const org = "11111111-1111-4111-8111-111111111111";
const id = "22222222-2222-4222-8222-222222222222";
const owner = ["organizations", org, "my-learning", id, "assignments", id, "files"];
const author = ["organizations", org, "courses", id, "material-files"];
const context = (path: string[]) => ({ params: Promise.resolve({ path }) });
const url = (path: string[]) => `http://localhost:3000/api/courses/${path.join("/")}`;
const headers = { origin: "http://localhost:3000", "x-csrf-token": "csrf", "content-type": "application/json" };

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("learning file BFF", () => {
  it("streams the exact scoped raw PUT with server credentials and a pinned version", async () => {
    const bytes = "%PDF-1.4 synthetic learning bytes";
    const fetchMock = vi.fn(async (_url: string, init: RequestInit) => {
      expect(await new Response(init.body).text()).toBe(bytes);
      return Response.json({ file: { version: 3, state: "quarantined" } });
    });
    vi.stubGlobal("fetch", fetchMock);
    const path = [...owner, id, "content"];
    const response = await PUT(new NextRequest(url(path), { method: "PUT", body: bytes, headers: {
      ...headers, "content-type": "application/pdf", "if-match": '"1"', "X-BFF-Key": "untrusted", "X-Browser-Session": "untrusted",
    } }), context(path));
    expect(response.status).toBe(200);
    expect(fetchMock.mock.calls[0][0]).toBe(`http://api/api/v1/courses/${path.join("/")}`);
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ redirect: "error", headers: {
      "X-BFF-Key": "server-key", "X-Browser-Session": "session", "Content-Type": "application/pdf", "If-Match": '"1"',
    } });
    expect(response.headers.get("cache-control")).toBe("private, no-store");
  });

  it("requires CSRF before reading bytes and rejects encodings, query tricks and generic writes", async () => {
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    const path = [...author, id, "content"];
    expect((await PUT(new NextRequest(url(path), { method: "PUT", body: "x", headers: { ...headers, origin: "https://foreign.example" } }), context(path))).status).toBe(403);
    expect((await PUT(new NextRequest(url(path), { method: "PUT", body: "x", headers: { ...headers, "content-type": "application/pdf", "if-match": '"1"', "content-encoding": "gzip" } }), context(path))).status).toBe(400);
    expect((await GET(new NextRequest(url(path) + "?owner=other"), context(path))).status).toBe(404);
    expect((await POST(new NextRequest(url(path), { method: "POST", headers, body: "{}" }), context(path))).status).toBe(404);
    expect((await PUT(new NextRequest(url([...path, "other"]), { method: "PUT", headers, body: "{}" }), context([...path, "other"]))).status).toBe(404);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("generates a safe learning filename and drops private provider headers", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("%PDF", { headers: {
      "content-type": "application/pdf", "content-length": "4", "content-disposition": "inline; filename=secret", "x-storage-key": "secret", "set-cookie": "secret=value",
    } })));
    const path = [...author, id, "content"];
    const result = await GET(new NextRequest(url(path)), context(path));
    expect(await result.text()).toBe("%PDF");
    expect(result.headers.get("content-disposition")).toBe(`attachment; filename="learning-file-${id}.pdf"`);
    expect(result.headers.get("content-security-policy")).toContain("sandbox");
    expect(result.headers.has("x-storage-key")).toBe(false);
    expect(result.headers.has("set-cookie")).toBe(false);
  });

  it("bounds UTF-8 JSON commands and reconciles removal using the binding version", async () => {
    const fetchMock = vi.fn().mockImplementation(async () => Response.json({ state: "removed", version: 2 }));
    vi.stubGlobal("fetch", fetchMock);
    const path = [...author, id];
    const result = await DELETE(new NextRequest(url(path), { method: "DELETE", headers, body: '{"expected_version":1}' }), context(path));
    expect(result.status).toBe(200);
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: "DELETE", body: '{"expected_version":1}', redirect: "error" });
    fetchMock.mockClear();
    for (const body of ["{", new Uint8Array([0xff])]) {
      expect((await DELETE(new NextRequest(url(path), { method: "DELETE", headers, body }), context(path))).status).toBe(400);
    }
    expect((await DELETE(new NextRequest(url(path), { method: "DELETE", headers, body: "x".repeat(65537) }), context(path))).status).toBe(413);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("forwards only validated material cursors and protects the actor-bound delivery response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json({ items: [], next_cursor: null }));
    vi.stubGlobal("fetch", fetchMock);
    expect((await GET(new NextRequest(url(author) + `?limit=20&cursor=${id}`), context(author))).status).toBe(200);
    expect(fetchMock.mock.calls[0][0]).toBe(`http://api/api/v1/courses/${author.join("/")}?limit=20&cursor=${id}`);
    expect((await GET(new NextRequest(url(author) + "?limit=20&limit=30"), context(author))).status).toBe(404);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("%PDF", { headers: { "content-type": "application/pdf" } })));
    const token = ["organizations", org, "material-delivery", "payload.signature"];
    const delivered = await GET(new NextRequest(url(token)), context(token));
    expect(delivered.headers.get("content-security-policy")).toContain("sandbox");
    expect(delivered.headers.get("cache-control")).toBe("private, no-store");
    expect(await delivered.text()).toBe("%PDF");
  });
});
