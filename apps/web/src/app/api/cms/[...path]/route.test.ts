import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { GET, PATCH, POST, PUT } from "./route";

vi.mock("next/headers", () => ({ cookies: async () => ({ get: (name: string) => ({ value: name === "edp_csrf" ? "csrf" : "session" }) }) }));
vi.mock("../../../../lib/server-api", () => ({ cookieName: "edp_session", csrfName: "edp_csrf", settings: () => ({ api: "http://api", key: "private-key", origin: "http://localhost:3000" }) }));
const org = "11111111-1111-4111-8111-111111111111";
const id = "22222222-2222-4222-8222-222222222222";
const collection = ["organizations", org, "editorial"];
const context = (path = collection) => ({ params: Promise.resolve({ path }) });
function request(path = collection, method = "GET", query = "", body = "{}", origin = "http://localhost:3000", type = "application/json") {
  return new NextRequest(`http://localhost:3000/api/cms/${path.join("/")}${query ? `?${query}` : ""}`, { method, ...(method === "GET" ? {} : { body }), headers: { origin, "x-csrf-token": "csrf", "content-type": type } });
}
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("CMS editorial and media BFF", () => {
  it("rejects unbound scanner mutations and external paths before forwarding", async () => {
    const mock = vi.fn(); vi.stubGlobal("fetch", mock);
    const assets = ["organizations", org, "assets"];
    expect((await POST(request([...assets,id,"scan"], "POST"), context([...assets,id,"scan"]))).status).toBe(404);
    expect((await PUT(request([...assets,id,"content"], "PUT"), context([...assets,id,"content"]))).status).toBe(404);
    expect((await GET(request(), context(["https:", "outside.example"]))).status).toBe(404);
    expect(mock).not.toHaveBeenCalled();
  });
  it("streams only the scoped raw source with quoted version, origin, and server-held credentials", async()=>{
    const path=["organizations",org,"assets",id,"source","content"];
    const mock=vi.fn(async(_url:string,init:RequestInit)=>{expect(await new Response(init.body).text()).toBe("%PDF-synthetic");return Response.json({source:{state:"quarantined"}});});vi.stubGlobal("fetch",mock);
    const make=(type="application/pdf",origin="http://localhost:3000")=>new NextRequest(`http://localhost:3000/api/cms/${path.join("/")}`,{method:"PUT",body:"%PDF-synthetic",headers:{origin,"x-csrf-token":"csrf","content-type":type,"if-match":'"2"',"X-BFF-Key":"caller-secret"}});
    expect((await PUT(make("constructor"),context(path))).status).toBe(400);
    expect((await PUT(make("application/pdf","https://foreign.example"),context(path))).status).toBe(403);
    expect(mock).not.toHaveBeenCalled();
    expect((await PUT(make(),context(path))).status).toBe(200);
    expect(mock.mock.calls[0][1].headers).toMatchObject({"X-BFF-Key":"private-key","X-Browser-Session":"session","If-Match":'"2"'});
  });
  it("rejects invalid routes, queries, origin, JSON and byte size without forwarding", async () => {
    const mock = vi.fn(); vi.stubGlobal("fetch", mock);
    for (const query of ["locale=en&locale=ta", "limit=101", "api_key=secret", "cursor=../admin"]) expect((await GET(request(collection, "GET", query), context())).status).toBe(400);
    expect((await POST(request(collection, "POST", "", "{}", "https://outside.example"), context())).status).toBe(403);
    expect((await POST(request(collection, "POST", "limit=25"), context())).status).toBe(400);
    expect((await POST(request(collection, "POST", "", "{"), context())).status).toBe(400);
    expect((await POST(request(collection, "POST", "", "{}", "http://localhost:3000", "text/plain"), context())).status).toBe(400);
    expect((await POST(request(collection, "POST", "", JSON.stringify({ body: "அ".repeat(90000) })), context())).status).toBe(413);
    expect(mock).not.toHaveBeenCalled();
  });
  it("forwards bounded scoped filters and protects server credentials and response cookies", async () => {
    const mock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [], next_cursor: null }), { headers: { "set-cookie": "upstream=secret" } })); vi.stubGlobal("fetch", mock);
    const response = await GET(request(collection, "GET", `kind=event&locale=ta&slug=exact-address&cursor=${id}`), context());
    expect(mock.mock.calls[0][0]).toBe(`http://api/api/v1/cms/organizations/${org}/editorial?kind=event&locale=ta&slug=exact-address&cursor=${id}&limit=25`);
    expect(mock.mock.calls[0][1].headers).toMatchObject({ "X-BFF-Key": "private-key", "X-Browser-Session": "session" });
    expect(response.headers.get("set-cookie")).toBeNull();
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    expect(response.headers.get("x-robots-tag")).toBe("noindex, nofollow");
  });
  it("rejects malformed UTF-8 inside otherwise valid JSON instead of rewriting content", async () => {
    const mock = vi.fn(); vi.stubGlobal("fetch", mock);
    const bytes = new Uint8Array([...new TextEncoder().encode('{"title":"Synthetic '), 0xc3, 0x28, ...new TextEncoder().encode('","body":"Synthetic content"}')]);
    expect(() => JSON.parse(new TextDecoder().decode(bytes))).not.toThrow();
    const incoming = new NextRequest(`http://localhost:3000/api/cms/${collection.join("/")}`, { method: "POST", body: bytes,
      headers: { origin: "http://localhost:3000", "x-csrf-token": "csrf", "content-type": "application/json" } });
    const response = await POST(incoming, context());
    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({ error: { code: "invalid_request" } });
    expect(mock).not.toHaveBeenCalled();
  });
  it("forwards exact versioned JSON commands and returns upstream permission/version errors", async () => {
    const mock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code: "version_conflict" } }), { status: 409 })); vi.stubGlobal("fetch", mock);
    const path = [...collection, id];
    const body = JSON.stringify({ expected_version: 1, title: "Synthetic edit", body: "Synthetic content" });
    const response = await PATCH(request(path, "PATCH", "", body), context(path));
    expect(response.status).toBe(409);
    expect(await response.json()).toEqual({ error: { code: "version_conflict" } });
    expect(mock.mock.calls[0][0]).toBe(`http://api/api/v1/cms/${path.join("/")}`);
    expect(mock.mock.calls[0][1]).toMatchObject({ body, method: "PATCH", cache: "no-store" });
  });
});
