import {afterEach,describe,expect,it,vi} from "vitest";
import {NextRequest} from "next/server";
import {GET} from "./route";
vi.mock("../../../../lib/server-api",()=>({settings:()=>({api:"http://api"})}));
afterEach(()=>vi.unstubAllGlobals());
const org="11111111-1111-4111-8111-111111111111",id="22222222-2222-4222-8222-222222222222";
describe("public media gateway",()=>{
  it("only forwards the typed public asset path without browser credentials",async()=>{
    const mock=vi.fn<(url:string,init:RequestInit)=>Promise<Response>>().mockResolvedValue(new Response("synthetic",{headers:{"Content-Type":"image/png"}}));vi.stubGlobal("fetch",mock);
    const path=["organizations",org,"assets",id,"content"];
    const result=await GET(new NextRequest("http://local/api/public-media/"+path.join("/"),{headers:{"X-BFF-Key":"caller-secret","Cookie":"edp_session=secret"}}),{params:Promise.resolve({path})});
    expect(result.status).toBe(200);expect(mock.mock.calls[0][0]).toBe(`http://api/api/v1/public/organizations/${org}/assets/${id}/content`);
    expect(mock.mock.calls[0][1].headers).toEqual({});expect(await result.text()).toBe("synthetic");
    for(const invalid of [["organizations",org,"files",id,"content"],["https:","outside.example"],["organizations",org,"assets",id,"source","content"]])expect((await GET(new NextRequest("http://local/path"),{params:Promise.resolve({path:invalid})})).status).toBe(404);
    expect((await GET(new NextRequest("http://local/path?token=transferable"),{params:Promise.resolve({path})})).status).toBe(404);
    expect(mock).toHaveBeenCalledTimes(1);
  });
});
