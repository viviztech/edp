import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { DELETE, GET, POST, PUT } from "./route";
import { helpdeskFileMaxBytes } from "../../../../lib/helpdesk-file-transport";
vi.mock("next/headers", () => ({ cookies: async () => ({ get: (name: string) => ({ value: name === "edp_csrf" ? "csrf" : "session" }) }) }));
vi.mock("../../../../lib/server-api", () => ({ cookieName: "edp_session", csrfName: "edp_csrf", settings: () => ({ api: "http://api", key: "private-key", origin: "http://localhost:3000" }) }));
const org = "11111111-1111-4111-8111-111111111111";
const ticket = "22222222-2222-4222-8222-222222222222";
const path = ["organizations", org, "tickets", ticket, "messages"];
const context = (parts = path) => ({ params: Promise.resolve({ path: parts }) });
const request = (body: string, origin = "http://localhost:3000") => new NextRequest(`http://localhost:3000/api/helpdesk/${path.join("/")}`, { method: "POST",
  headers: { origin, "x-csrf-token": "csrf", "content-type": "application/json" }, body });
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });
describe("helpdesk BFF", () => {
  it("rejects invalid routes, origin, query and malformed body before forwarding", async () => {
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    expect((await GET(new NextRequest("http://localhost:3000/api/helpdesk/../auth"), context(["..", "auth"]))).status).toBe(404);
    expect((await POST(request("{}", "https://outside.example"), context())).status).toBe(403);
    expect((await POST(request("{"), context())).status).toBe(400);
    for (const query of ["limit=200", "status=open&status=closed", "api_key=secret"]) expect((await GET(new NextRequest(`http://localhost:3000/api/helpdesk/${path.join("/")}?${query}`), context())).status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("enforces streamed UTF-8 byte limit", async () => {
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    expect((await POST(request(JSON.stringify({ body: "அ".repeat(90000) })), context())).status).toBe(413);
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("forwards bounded JSON and browser session using server credentials without exposing cookies", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ version: 2 }), { status: 200, headers: { "set-cookie": "upstream=secret" } })); vi.stubGlobal("fetch", fetchMock);
    const response = await POST(request(JSON.stringify({ expected_version: 1, body: "Hello", internal: false })), context());
    expect(response.status).toBe(200); expect(response.headers.get("set-cookie")).toBeNull();
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    const [url, init] = fetchMock.mock.calls[0]; expect(url).toBe(`http://api/api/v1/helpdesk/${path.join("/")}`);
    expect(init.headers["X-BFF-Key"]).toBe("private-key"); expect(init.headers["X-Browser-Session"]).toBe("session");
    expect(init.headers["X-CSRF-Token"]).toBe("csrf"); expect(init.cache).toBe("no-store");
  });
  it("serves reauthorized text attachments as no-store nosniff downloads", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("தமிழ் receipt", { headers: { "content-disposition": "attachment; filename=receipt.txt", "content-type": "text/html" } })); vi.stubGlobal("fetch", fetchMock);
    const attachmentPath = ["organizations", org, "tickets", ticket, "attachments", ticket];
    const response = await GET(new NextRequest(`http://localhost:3000/api/helpdesk/${attachmentPath.join("/")}`), context(attachmentPath));
    expect(await response.text()).toBe("தமிழ் receipt"); expect(response.headers.get("content-type")).toBe("text/plain; charset=utf-8");
    expect(response.headers.get("x-content-type-options")).toBe("nosniff"); expect(response.headers.get("content-disposition")).toBe("attachment; filename=receipt.txt");
    expect(response.headers.get("cache-control")).toBe("private, no-store");
  });
  it("does not transform attachment access errors into downloadable content and caps upstream attachment size", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ error: { code: "forbidden" } }), { status: 403 }))
      .mockResolvedValueOnce(new Response("x".repeat(32769))); vi.stubGlobal("fetch", fetchMock);
    const parts = ["organizations", org, "tickets", ticket, "attachments", ticket]; const req = () => new NextRequest(`http://localhost:3000/api/helpdesk/${parts.join("/")}`);
    const denied = await GET(req(), context(parts)); expect(denied.status).toBe(403); expect(denied.headers.get("content-disposition")).toBeNull();
    expect((await GET(req(), context(parts))).status).toBe(502);
  });
  it("returns an unavailable response for upstream network failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("timeout")));
    expect((await POST(request("{}"), context())).status).toBe(503);
  });
  it("streams only exact scoped file content with MIME/version, CSRF and server credentials",async()=>{
    const parts=["organizations",org,"tickets",ticket,"files",ticket,"content"];
    const mock=vi.fn(async(_url:string,init:RequestInit)=>{expect(await new Response(init.body).text()).toBe("%PDF-synthetic");return Response.json({state:"staged",file:{state:"quarantined"}});});vi.stubGlobal("fetch",mock);
    const make=(media="application/pdf",origin="http://localhost:3000",extra:Record<string,string>={})=>new NextRequest(`http://localhost:3000/api/helpdesk/${parts.join("/")}`,{method:"PUT",body:"%PDF-synthetic",headers:{origin,"content-type":media,"if-match":'"3"',"x-csrf-token":"csrf","X-BFF-Key":"browser",...extra}});
    for(const media of ["constructor","toString","__proto__","text/html"]){expect((await PUT(make(media),context(parts))).status).toBe(400);}
    expect((await PUT(make("application/pdf","https://other.example"),context(parts))).status).toBe(403);
    expect((await PUT(make("application/pdf",undefined,{"if-match":"3"}),context(parts))).status).toBe(400);
    expect((await PUT(make("application/pdf",undefined,{"content-encoding":"gzip"}),context(parts))).status).toBe(400);
    expect((await PUT(make("application/pdf",undefined,{"content-length":String(helpdeskFileMaxBytes+1)}),context(parts))).status).toBe(413);
    expect(mock).not.toHaveBeenCalled();
    expect((await PUT(make(),context(parts))).status).toBe(200);expect(mock.mock.calls[0][1].headers).toMatchObject({"X-BFF-Key":"private-key","X-Browser-Session":"session","If-Match":'"3"'});
  });
  it("uses binding-based safe download names and keeps file removal a bounded JSON command",async()=>{
    const parts=["organizations",org,"tickets",ticket,"files",ticket];
    const mock=vi.fn().mockResolvedValueOnce(new Response("private file",{headers:{"content-type":"text/plain; charset=utf-8","content-length":"12","set-cookie":"secret=value","content-disposition":"inline; filename=provider-secret"}})).mockResolvedValueOnce(Response.json({state:"removed",version:4}));vi.stubGlobal("fetch",mock);
    const result=await GET(new NextRequest(`http://localhost:3000/api/helpdesk/${[...parts,"content"].join("/")}`),context([...parts,"content"]));
    expect(await result.text()).toBe("private file");expect(result.headers.get("content-disposition")).toBe(`attachment; filename="helpdesk-file-${ticket}.txt"`);expect(result.headers.has("set-cookie")).toBe(false);expect(result.headers.get("content-security-policy")).toContain("sandbox");
    const remove=new NextRequest(`http://localhost:3000/api/helpdesk/${parts.join("/")}`,{method:"DELETE",body:'{"expected_version":3}',headers:{origin:"http://localhost:3000","x-csrf-token":"csrf","content-type":"application/json"}});
    expect((await DELETE(remove,context(parts))).status).toBe(200);expect(mock.mock.calls[1][1]).toMatchObject({method:"DELETE",body:'{"expected_version":3}'});
    expect((await GET(new NextRequest(`http://localhost:3000/api/helpdesk/${parts.join("/")}?internal=true`),context(parts))).status).toBe(400);
  });
});
