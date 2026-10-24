import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import MediaMetadata from "./view";
import { mediaAdminMessages } from "../../../../lib/media-admin-messages";

const org="11111111-1111-4111-8111-111111111111",id="22222222-2222-4222-8222-222222222222";
const base=`/api/cms/organizations/${org}/assets`;
const legacy={id,filename:"synthetic.pdf",title:"Synthetic media",media_type:"application/pdf",byte_size:15,scan_status:"clean",visibility:"private",public_url:null,version:1,byte_state:"unbacked",source:null,prepared:null,can_publish:false};
const policy={enabled:true,max_upload_bytes:10485760,policy:{id:org,name:"Synthetic policy",notice_en:"Synthetic collection notice",notice_ta:"செயற்கை அறிவிப்பு",max_file_bytes:1024,max_files:2,allowed_mime_types:["application/pdf"]}};
const pending={...legacy,version:2,byte_state:"pending",source:{id,version:1,state:"pending",failure_code:null}};
const clean={...pending,byte_state:"clean",can_publish:true,source:{...pending.source,version:5,state:"clean"}};
const json=(body:unknown,status=200)=>Response.json(body,{status});
afterEach(()=>{cleanup();vi.unstubAllGlobals();vi.restoreAllMocks();});

describe("secure media workspace",()=>{
  it("keeps legacy metadata honest and hides mutation controls for view-only staff in Tamil",async()=>{
    const mock=vi.fn(async(url:string)=>json(url.endsWith("/policy")?policy:{items:[legacy],next_cursor:null}));vi.stubGlobal("fetch",mock);
    await act(async()=>{render(<MediaMetadata org={org} locale="ta" permissions={["cms.asset.view"]}/>);});
    expect(screen.getByText(mediaAdminMessages.ta.unbacked)).toBeTruthy();
    expect(screen.queryByRole("link")).toBeNull();expect(screen.queryByLabelText(mediaAdminMessages.ta.file)).toBeNull();
    expect(screen.getByText(mediaAdminMessages.ta.boundary)).toBeTruthy();
  });
  it("keeps records after failed pagination and retries the exact cursor",async()=>{
    let pages=0;const mock=vi.fn(async(url:string)=>{if(url.endsWith("/policy"))return json(policy);if(url.includes("?cursor="))return ++pages===1?json({},503):json({items:[{...legacy,id:org,title:"Next media"}],next_cursor:null});return json({items:[legacy],next_cursor:id});});vi.stubGlobal("fetch",mock);
    await act(async()=>{render(<MediaMetadata org={org} locale="en"/>);});
    await act(async()=>{fireEvent.click(screen.getByRole("button",{name:"Load more"}));});expect(screen.getByText("Synthetic media")).toBeTruthy();
    await act(async()=>{fireEvent.click(screen.getByRole("button",{name:"Load more"}));});expect(screen.getByText("Next media")).toBeTruthy();
    expect(mock.mock.calls.filter(call=>call[0].includes("?cursor="))).toEqual([[`${base}?cursor=${id}`,{cache:"no-store"}],[`${base}?cursor=${id}`,{cache:"no-store"}]]);
  });
  it("reconciles a committed upload with lost response before retry and retains the selected file",async()=>{
    vi.stubGlobal("crypto",{randomUUID:()=>id,subtle:{digest:async()=>new Uint8Array(32).buffer}});
    let committed=false;const mock=vi.fn(async(url:string,init?:RequestInit)=>{
      if(url==="/api/session/csrf")return json({csrf_token:"csrf-from-endpoint"});
      if(url.endsWith("/policy"))return json(policy);
      if(url===base&&init?.method==="POST")return json(legacy,201);
      if(url.endsWith("/source")&&init?.method==="POST")return json(pending,201);
      if(init?.method==="PUT"){committed=true;throw new Error("Connection lost");}
      if(url===base+"/"+id)return json(committed?{...pending,source:{...pending.source,state:"quarantined",version:3}}:pending);
      return json({items:[],next_cursor:null});
    });vi.stubGlobal("fetch",mock);
    await act(async()=>{render(<MediaMetadata org={org} locale="en" permissions={["cms.asset.view","cms.asset.create"]}/>);});
    const file=new File(["%PDF-synthetic"],"synthetic.pdf",{type:"application/pdf"});Object.defineProperty(file,"arrayBuffer",{value:async()=>new TextEncoder().encode("%PDF-synthetic").buffer});
    fireEvent.change(screen.getByLabelText("Media title"),{target:{value:"Draft title"}});fireEvent.change(screen.getByLabelText("Source file"),{target:{files:[file]}});
    await act(async()=>{fireEvent.click(screen.getByRole("button",{name:"Register and upload"}));});
    expect(screen.getByLabelText("Media title")).toHaveProperty("value","Draft title");expect(screen.getByText(/synthetic.pdf \(/)).toBeTruthy();
    await act(async()=>{fireEvent.click(screen.getByRole("button",{name:"Retry this registration or upload"}));});
    expect(mock.mock.calls.filter(call=>call[1]?.method==="PUT")).toHaveLength(1);
    expect(mock.mock.calls.filter(call=>call[1]?.method==="POST")).toHaveLength(2);
    expect(screen.getByRole("status").textContent).toContain("Saved");
  });
  it("freezes writes while publishing and retains the explicit reason after stale rejection",async()=>{
    let finish!:(value:Response)=>void;const write=new Promise<Response>(resolve=>{finish=resolve;});
    const mock=vi.fn(async(url:string,init?:RequestInit)=>{if(url==="/api/session/csrf")return json({csrf_token:"csrf-from-endpoint"});if(init?.method==="POST")return write;if(url.endsWith("/policy"))return json(policy);if(url===base+"/"+id)return json(clean);return json({items:[clean],next_cursor:null});});vi.stubGlobal("fetch",mock);
    await act(async()=>{render(<MediaMetadata org={org} locale="en" permissions={["cms.asset.view","cms.asset.publish"]}/>);});
    await act(async()=>{fireEvent.click(screen.getByRole("button",{name:"Inspect media: Synthetic media"}));});
    fireEvent.change(screen.getByLabelText("Reason for preparation, publication or revocation"),{target:{value:"Approved synthetic publication"}});
    await act(async()=>{fireEvent.click(screen.getByRole("button",{name:"Publish media"}));});
    expect(screen.getByRole("button",{name:"Publish media"})).toHaveProperty("disabled",true);
    await act(async()=>{finish(json({error:{code:"version_conflict"}},409));});
    expect(screen.getByRole("status").textContent).toContain("record changed");
    expect(screen.getByLabelText("Reason for preparation, publication or revocation")).toHaveProperty("value","Approved synthetic publication");
  });
  it("obtains endpoint CSRF tokens for metadata and raw bytes when cookies are HttpOnly",async()=>{
    vi.spyOn(document,"cookie","get").mockReturnValue("");
    vi.stubGlobal("crypto",{randomUUID:()=>id,subtle:{digest:async()=>new Uint8Array(32).buffer}});
    let issued=0;
    const mock=vi.fn(async(url:string,init?:RequestInit)=>{
      if(url==="/api/session/csrf")return json({csrf_token:`endpoint-token-${++issued}`});
      if(init?.method==="POST"||init?.method==="PUT"){
        if(new Headers(init.headers).get("X-CSRF-Token")!==`endpoint-token-${issued}`||!issued)return json({},403);
        if(init.method==="PUT")return json({...pending,source:{...pending.source,state:"quarantined",version:3}});
        return json(url.endsWith("/source")?pending:legacy,201);
      }
      if(url===base+"/"+id)return json(pending);
      return json(url.endsWith("/policy")?policy:{items:[],next_cursor:null});
    });vi.stubGlobal("fetch",mock);
    await act(async()=>{render(<MediaMetadata org={org} locale="en" permissions={["cms.asset.view","cms.asset.create"]}/>);});
    const file=new File(["%PDF-synthetic"],"synthetic.pdf",{type:"application/pdf"});Object.defineProperty(file,"arrayBuffer",{value:async()=>new TextEncoder().encode("%PDF-synthetic").buffer});
    const chooser=screen.getByLabelText("Source file") as HTMLInputElement;
    fireEvent.change(screen.getByLabelText("Media title"),{target:{value:"HTTP-only cookie upload"}});fireEvent.change(chooser,{target:{files:[file]}});
    await act(async()=>{fireEvent.click(screen.getByRole("button",{name:"Register and upload"}));});
    expect(issued).toBe(3);
    const writes=mock.mock.calls.filter(call=>call[1]?.method==="POST"||call[1]?.method==="PUT");
    expect(writes).toHaveLength(3);
    expect(writes.map(call=>new Headers(call[1]?.headers).get("X-CSRF-Token"))).toEqual(["endpoint-token-1","endpoint-token-2","endpoint-token-3"]);
    expect(screen.getByRole("status").textContent).toContain("Saved");
    const cleared=screen.getByLabelText("Source file") as HTMLInputElement;
    expect(cleared).not.toBe(chooser);expect(cleared.files).toHaveLength(0);
    fireEvent.change(screen.getByLabelText("Media title"),{target:{value:"Same file new record"}});fireEvent.change(cleared,{target:{files:[file]}});
    expect(screen.getByRole("button",{name:"Register and upload"})).toHaveProperty("disabled",false);
  });
  it("retains the selected file and sends no metadata when the CSRF endpoint fails",async()=>{
    vi.stubGlobal("crypto",{randomUUID:()=>id});
    const mock=vi.fn(async(url:string,init?:RequestInit)=>{if(init?.method&&init.method!=="GET")throw new Error("Unexpected write");return url==="/api/session/csrf"?json({},503):json(url.endsWith("/policy")?policy:{items:[],next_cursor:null});});vi.stubGlobal("fetch",mock);
    await act(async()=>{render(<MediaMetadata org={org} locale="en" permissions={["cms.asset.view","cms.asset.create"]}/>);});
    const chooser=screen.getByLabelText("Source file") as HTMLInputElement;
    const file=new File(["%PDF-synthetic"],"synthetic.pdf",{type:"application/pdf"});
    fireEvent.change(screen.getByLabelText("Media title"),{target:{value:"Retained title"}});fireEvent.change(chooser,{target:{files:[file]}});
    await act(async()=>{fireEvent.click(screen.getByRole("button",{name:"Register and upload"}));});
    expect(mock.mock.calls.filter(call=>call[1]?.method==="POST"||call[1]?.method==="PUT")).toHaveLength(0);
    expect(screen.getByLabelText("Media title")).toHaveProperty("value","Retained title");
    expect(screen.getByText(/synthetic.pdf \(/)).toBeTruthy();
    expect(screen.getByRole("button",{name:"Retry this registration or upload"})).toBeTruthy();
    expect(screen.getByRole("status").textContent).toBe(mediaAdminMessages.en.error);
    expect(screen.getByLabelText("Source file")).toBe(chooser);expect(chooser.files).toHaveLength(1);
    fireEvent.click(screen.getByRole("button",{name:"Start a new registration"}));
    const cleared=screen.getByLabelText("Source file") as HTMLInputElement;
    expect(cleared).not.toBe(chooser);expect(cleared.files).toHaveLength(0);
    fireEvent.change(screen.getByLabelText("Media title"),{target:{value:"Same file after discard"}});fireEvent.change(cleared,{target:{files:[file]}});
    expect(screen.getByRole("button",{name:"Register and upload"})).toHaveProperty("disabled",false);
  });
});
