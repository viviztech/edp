import {afterEach,describe,expect,it,vi} from "vitest";
import {cmsFileMaxBytes,cmsFileTransport} from "./cms-file-transport";

const id="22222222-2222-4222-8222-222222222222";
const request=(media="image/png",extra:Record<string,string>={})=>new Request("http://local/source",{method:"PUT",headers:{"Content-Type":media,"If-Match":'"1"',...extra},body:"synthetic"});
afterEach(()=>vi.unstubAllGlobals());
describe("CMS media byte boundary",()=>{
  it("rejects prototype names, non-CMS formats, encodings and oversized declared bytes before fetch",async()=>{
    const mock=vi.fn();vi.stubGlobal("fetch",mock);
    for(const media of ["constructor","toString","__proto__","text/plain","image/svg+xml","image/png; charset=utf-8"]){expect((await cmsFileTransport(request(media),"http://unused",{},id)).status).toBe(400);}
    expect((await cmsFileTransport(request("image/png",{"Content-Encoding":"gzip"}),"http://unused",{},id)).status).toBe(400);
    expect((await cmsFileTransport(request("image/png",{"Content-Length":String(cmsFileMaxBytes+1)}),"http://unused",{},id)).status).toBe(413);
    expect(mock).not.toHaveBeenCalled();
  });
  it("counts upload bytes without trusting Content-Length and stops unread sources on rejection",async()=>{
    let canceled=false,sent=0;
    const block=new Uint8Array(1048576),body=new ReadableStream({pull(controller){controller.enqueue(block);if(++sent===11)controller.close();},cancel(){canceled=true;}});
    vi.stubGlobal("fetch",vi.fn(async(_url:string,init:RequestInit)=>{await new Response(init.body).arrayBuffer();return Response.json({});}));
    const put=new Request("http://local/source",{method:"PUT",headers:{"Content-Type":"image/png","If-Match":'"1"'},body,duplex:"half"} as RequestInit&{duplex:string});
    expect((await cmsFileTransport(put,"http://unused",{},id)).status).toBe(413);
    vi.stubGlobal("fetch",vi.fn(async()=>Response.json({error:{code:"forbidden"}},{status:403})));
    const unread=new Request("http://local/source",{method:"PUT",headers:{"Content-Type":"image/png","If-Match":'"1"'},body:new ReadableStream({pull(controller){controller.enqueue(block);},cancel(){canceled=true;}}),duplex:"half"} as RequestInit&{duplex:string});
    expect((await cmsFileTransport(unread,"http://unused",{},id)).status).toBe(403);expect(canceled).toBe(true);
  });
  it("only inlines allowed public images and keeps PDFs attachments with safe headers",async()=>{
    for(const media of ["image/png","application/pdf","constructor"]){
      vi.stubGlobal("fetch",vi.fn(async()=>new Response("synthetic",{headers:{"Content-Type":media,"Content-Length":"9","Set-Cookie":"provider-secret","Content-Disposition":"inline; filename=unsafe"}})));
      const response=await cmsFileTransport(new Request("http://local/public"),"http://unused",{},id,true);
      if(media==="constructor"){expect(response.status).toBe(502);continue;}
      expect(response.headers.get("content-disposition")).toContain(media==="image/png"?"inline;":"attachment;");
      expect(response.headers.get("content-disposition")).toContain(id);
      expect(response.headers.has("set-cookie")).toBe(false);expect(response.headers.get("cache-control")).toBe("private, no-store");
      expect(response.headers.get("content-security-policy")).toContain("sandbox");expect(await response.text()).toBe("synthetic");
    }
  });
  it("errors on truncated or oversized download streams",async()=>{
    vi.stubGlobal("fetch",vi.fn(async()=>new Response("short",{headers:{"Content-Type":"image/png","Content-Length":"9"}})));
    const result=await cmsFileTransport(new Request("http://local/public"),"http://unused",{},id,true);
    await expect(result.arrayBuffer()).rejects.toThrow("invalid_upstream");
    let sent=0;const block=new Uint8Array(1048576);
    vi.stubGlobal("fetch",vi.fn(async()=>new Response(new ReadableStream({pull(controller){controller.enqueue(block);if(++sent===11)controller.close();}}),{headers:{"Content-Type":"image/png"}})));
    const oversized=await cmsFileTransport(new Request("http://local/public"),"http://unused",{},id,true);await expect(oversized.arrayBuffer()).rejects.toThrow("invalid_upstream");
  });
});
