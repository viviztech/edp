import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { GET, POST } from "./route";
import { POST as impactPost } from "../../impact/[...path]/route";

vi.mock("next/headers", () => ({ cookies: async () => ({ get: (name: string) => ({ value: name === "edp_csrf" ? "csrf" : "session" }) }) }));
vi.mock("../../../../lib/server-api", () => ({ cookieName: "edp_session", csrfName: "edp_csrf", settings: () => ({ api: "http://api", key: "server-key", origin: "http://localhost:3000" }) }));
const org = "11111111-1111-4111-8111-111111111111"; const item = "22222222-2222-4222-8222-222222222222";
const context = (path: string[]) => ({ params: Promise.resolve({ path }) });
const request = (path: string[], method = "GET", body?: string, query = "", origin = "http://localhost:3000") => new NextRequest(`http://localhost:3000/api/reports/${path.join("/")}${query}`, { method, headers: { origin, "content-type": "application/json", "x-csrf-token": "csrf" }, ...(body !== undefined ? { body } : {}) });
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });
describe("report/impact BFF", () => {
  it("rejects unsupported paths, repeated filters and cross-origin writes before forwarding", async () => {
    const upstream = vi.fn(); vi.stubGlobal("fetch", upstream); const snapshots = ["organizations", org, "snapshots"];
    expect((await GET(request(["..", "auth"]), context(["..", "auth"]))).status).toBe(404);
    expect((await GET(request(snapshots, "GET", undefined, "?limit=25&limit=50"), context(snapshots))).status).toBe(400);
    expect((await POST(request(snapshots, "POST", "{}", "", "https://foreign.example"), context(snapshots))).status).toBe(403);
    expect((await POST(request(snapshots, "POST", "{}", "?cursor=" + item), context(snapshots))).status).toBe(400);
    expect(upstream).not.toHaveBeenCalled();
  });
  it("bounds streamed UTF-8 JSON and authenticates impact mutations", async () => {
    const upstream = vi.fn().mockResolvedValue(new Response("{}", { status: 201 })); vi.stubGlobal("fetch", upstream); const records = ["organizations", org, "records"];
    expect((await impactPost(request(records, "POST", JSON.stringify({ reason: "அ".repeat(30000) })), context(records))).status).toBe(413);
    expect((await impactPost(request(records, "POST", "{"), context(records))).status).toBe(400);
    expect(upstream).not.toHaveBeenCalled();
    expect((await impactPost(request(records, "POST", JSON.stringify({ reason: "Valid reason" })), context(records))).status).toBe(201);
    expect(upstream.mock.calls[0][0]).toBe(`http://api/api/v1/impact/organizations/${org}/records`);
    expect(upstream.mock.calls[0][1].headers["X-Browser-Session"]).toBe("session");
  });
  it("preserves CSV bytes with private attachment headers and never reflects upstream headers", async () => {
    const csv = new TextEncoder().encode('\uFEFFmetric,value\r\n"தமிழ்",3\r\n');
    const upstream = vi.fn().mockResolvedValue(new Response(csv, { status: 200, headers: { "Content-Type": "text/csv; charset=utf-8", "Content-Disposition": 'inline; filename="untrusted.html"', "Set-Cookie": "secret=bad" } })); vi.stubGlobal("fetch", upstream);
    const path = ["organizations", org, "exports", item, "download", "a".repeat(43)]; const response = await GET(request(path), context(path));
    expect([...new Uint8Array(await response.arrayBuffer())]).toEqual([...csv]); expect(response.headers.get("cache-control")).toBe("private, no-store");
    expect(response.headers.get("content-disposition")).toBe('attachment; filename="impact-report.csv"'); expect(response.headers.get("x-content-type-options")).toBe("nosniff"); expect(response.headers.get("set-cookie")).toBeNull();
  });
  it("rejects download query overrides, wrong media and excessive CSV output", async () => {
    const path = ["organizations", org, "exports", item, "download", "a".repeat(43)]; const upstream = vi.fn().mockResolvedValueOnce(new Response("<html/>", { headers: { "Content-Type": "text/html" } })).mockResolvedValueOnce(new Response("x".repeat(262145), { headers: { "Content-Type": "text/csv" } })); vi.stubGlobal("fetch", upstream);
    expect((await GET(request(path, "GET", undefined, "?limit=25"), context(path))).status).toBe(400);
    expect((await GET(request(path), context(path))).status).toBe(502); expect((await GET(request(path), context(path))).status).toBe(502);
    expect(upstream).toHaveBeenCalledTimes(2);
  });
});
