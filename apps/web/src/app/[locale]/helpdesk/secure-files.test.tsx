import {afterEach,describe,expect,it,vi} from "vitest";
import {act,cleanup,fireEvent,render,screen} from "@testing-library/react";
import {useState} from "react";
import type {components} from "../../../lib/api-contracts";
import SecureHelpdeskFiles,{PostedHelpdeskFiles} from "./secure-files";
import {secureFileWords} from "./secure-files-content";

type Item=components["schemas"]["HelpdeskFileView"];
const org="11111111-1111-4111-8111-111111111111",ticket="22222222-2222-4222-8222-222222222222",id="33333333-3333-4333-8333-333333333333",other="44444444-4444-4444-8444-444444444444";
const base=`/api/helpdesk/organizations/${org}/tickets/${ticket}`,time="2026-10-23T08:00:00Z";
const policy={id:org,edition:1,name:"Synthetic attachment policy",allowed_mime_types:["application/pdf" as const],max_file_bytes:1024,max_upload_bytes:1024,max_files:2,retention_days:1,rejected_retention_days:1,notice_en:"Synthetic attachment notice",notice_ta:"செயற்கை இணைப்பு அறிவிப்பு",allow_frozen_disposal:false};
function item(changes:Partial<Item>={}):Item{return {id,message_id:null,internal:false,state:"staged",version:3,policy,usable:false,evidence:null,file:{id:other,organization_id:org,owner_person_id:other,purpose:"helpdesk_attachment",resource_id:id,policy_id:org,client_request_id:id,media_type:"application/pdf",byte_size:14,sha256:"a".repeat(64),state:"pending",version:7,verified_at:null,scanned_at:null,scan_attempts:0,failure_code:null,retention_until:"2099-01-01T00:00:00Z",legal_hold:false,evidence_frozen:false,deleted_at:null,created_at:time,updated_at:time},...changes};}
const clean=item({usable:true,file:{...item().file,state:"clean"}});
const batch=(items:Item[])=>({collection_enabled:true,max_upload_bytes:10485760,policy,items,next_cursor:null});
const json=(data:unknown,status=200)=>Response.json(data,{status});
const busy=vi.fn(),dirty=vi.fn();
function Harness({internal=false,revision=0}:{internal?:boolean;revision?:number}){const[selected,setSelected]=useState<string[]>([]);return <><output data-testid="selection">{selected.join(",")}</output><SecureHelpdeskFiles base={base} locale="en" internal={internal} disabled={false} selected={selected} onSelect={setSelected} onBusy={busy} onDirty={dirty} revision={revision}/></>;}
afterEach(()=>{cleanup();vi.useRealTimers();vi.unstubAllGlobals();vi.restoreAllMocks();busy.mockClear();dirty.mockClear();});

describe("helpdesk secure attachment staging",()=>{
  it("offers only clean matching-visibility staged files and never selects them automatically",async()=>{
    vi.stubGlobal("fetch",vi.fn(async()=>json(batch([clean,{...clean,id:other,internal:true}]))));
    let view!:ReturnType<typeof render>;await act(async()=>{view=render(<Harness/>);});
    expect(screen.getAllByText("Synthetic attachment notice").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Attach this clean file 1")).toHaveProperty("disabled",false);
    expect(screen.getByLabelText("Attach this clean file 2")).toHaveProperty("disabled",true);
    expect(screen.getByTestId("selection").textContent).toBe("");fireEvent.click(screen.getByLabelText("Attach this clean file 1"));expect(screen.getByTestId("selection").textContent).toBe(id);
    await act(async()=>{view.rerender(<Harness internal/>);});expect(screen.getByTestId("selection").textContent).toBe("");
    expect(screen.getByLabelText("Attach this clean file 1")).toHaveProperty("disabled",true);expect(screen.getByLabelText("Attach this clean file 2")).toHaveProperty("disabled",false);
  });
  it("recovers a lost committed PUT by reading binding state before retrying",async()=>{
    vi.stubGlobal("crypto",{randomUUID:()=>id,subtle:{digest:async()=>new Uint8Array(32).buffer}});
    let committed=false;const mock=vi.fn(async(url:string,init?:RequestInit)=>{
      if(url==="/api/session/csrf")return json({csrf_token:"csrf"});
      if(init?.method==="POST")return json(item(),201);
      if(init?.method==="PUT"){committed=true;throw new Error("Lost response");}
      if(url.endsWith("/"+id))return json(committed?item({file:{...item().file,state:"quarantined",version:9}}):item());
      return json(batch([]));
    });vi.stubGlobal("fetch",mock);
    await act(async()=>{render(<Harness/>);});const file=Object.assign(new File(["%PDF-synthetic"],"receipt.pdf",{type:"application/pdf"}),{arrayBuffer:async()=>new TextEncoder().encode("%PDF-synthetic").buffer});
    fireEvent.change(screen.getByLabelText("Choose a secure file"),{target:{files:[file]}});
    await act(async()=>{fireEvent.click(screen.getByRole("button",{name:"Upload private file"}));});
    expect(screen.getByText("receipt.pdf (14 bytes)")).toBeTruthy();expect(screen.getByLabelText("Choose a secure file")).toHaveProperty("disabled",true);
    await act(async()=>{fireEvent.click(screen.getByRole("button",{name:"Retry the same upload"}));});
    expect(mock.mock.calls.filter(call=>call[1]?.method==="PUT")).toHaveLength(1);expect(mock.mock.calls.filter(call=>call[1]?.method==="POST")).toHaveLength(1);
    expect(screen.getByLabelText("Attach this clean file 1")).toHaveProperty("disabled",true);
    expect(screen.getAllByText(secureFileWords.en.scanWait).length).toBeGreaterThan(0);
  });
  it("polls bounded scanner status but waits for a server clean verdict and explicit selection",async()=>{
    vi.useFakeTimers();let calls=0;vi.stubGlobal("fetch",vi.fn(async()=>json(batch([++calls===1?item({file:{...item().file,state:"quarantined",failure_code:"scan_unavailable"}}):clean]))));
    await act(async()=>{render(<Harness/>);});expect(screen.getByText(secureFileWords.en.scanUnavailable)).toBeTruthy();expect(screen.getByLabelText("Attach this clean file 1")).toHaveProperty("disabled",true);
    await act(async()=>{await vi.advanceTimersByTimeAsync(2000);});expect(screen.getByLabelText("Attach this clean file 1")).toHaveProperty("disabled",false);expect(screen.getByTestId("selection").textContent).toBe("");expect(calls).toBe(2);
  });
  it("stops automatic polling after ten pending checks and never infers a clean result",async()=>{
    vi.useFakeTimers();const mock=vi.fn(async()=>json(batch([item({file:{...item().file,state:"quarantined",failure_code:"scan_unavailable"}})])));vi.stubGlobal("fetch",mock);
    await act(async()=>{render(<Harness/>);});
    for(let attempt=0;attempt<10;attempt++)await act(async()=>{await vi.advanceTimersByTimeAsync(2000);});
    expect(mock).toHaveBeenCalledTimes(11);expect(screen.getByText(secureFileWords.en.pollStopped)).toBeTruthy();
    await act(async()=>{await vi.advanceTimersByTimeAsync(60000);});expect(mock).toHaveBeenCalledTimes(11);expect(screen.getByLabelText("Attach this clean file 1")).toHaveProperty("disabled",true);
  });
  it("retains the local file when recovered clean evidence has already expired",async()=>{
    vi.stubGlobal("crypto",{randomUUID:()=>id,subtle:{digest:async()=>new Uint8Array(32).buffer}});
    vi.stubGlobal("fetch",vi.fn(async(url:string,init?:RequestInit)=>url==="/api/session/csrf"?json({csrf_token:"csrf"}):init?.method==="POST"||url.endsWith("/"+id)?json({...clean,usable:false}):json(batch([]))));
    await act(async()=>{render(<Harness/>);});const file=Object.assign(new File(["%PDF-synthetic"],"expired.pdf",{type:"application/pdf"}),{arrayBuffer:async()=>new TextEncoder().encode("%PDF-synthetic").buffer});
    fireEvent.change(screen.getByLabelText("Choose a secure file"),{target:{files:[file]}});
    await act(async()=>{fireEvent.click(screen.getByRole("button",{name:"Upload private file"}));});
    expect(screen.getByText("expired.pdf (14 bytes)")).toBeTruthy();expect(screen.getByText(secureFileWords.en.error)).toBeTruthy();expect(screen.getByRole("button",{name:"Retry the same upload"})).toBeTruthy();expect(screen.getByLabelText("Attach this clean file 1")).toHaveProperty("disabled",true);
  });
  it("removes staged metadata with binding version and clears selected already-posted evidence on refresh",async()=>{
    let removed=false,posted=false;const mock=vi.fn(async(url:string,init?:RequestInit)=>{if(url==="/api/session/csrf")return json({csrf_token:"csrf"});if(init?.method==="DELETE"){removed=true;return json({...clean,state:"removed",version:4});}return json(batch(removed?[]:[posted?{...clean,state:"posted",message_id:other}:clean]));});vi.stubGlobal("fetch",mock);
    let view!:ReturnType<typeof render>;await act(async()=>{view=render(<Harness/>);});fireEvent.click(screen.getByLabelText("Attach this clean file 1"));expect(screen.getByTestId("selection").textContent).toBe(id);
    posted=true;await act(async()=>{view.rerender(<Harness revision={1}/>);});expect(screen.getByTestId("selection").textContent).toBe("");
    posted=false;await act(async()=>{view.rerender(<Harness revision={2}/>);});
    await act(async()=>{fireEvent.click(screen.getByRole("button",{name:"Remove staged file 1"}));});
    expect(mock.mock.calls.find(call=>call[1]?.method==="DELETE")?.[1]?.body).toBe('{"expected_version":3}');expect(screen.queryByLabelText("Attach this clean file 1")).toBeNull();
  });
  it("reconciles explicitly selected later-page files after a lost message response",async()=>{
    let posted=false;const mock=vi.fn(async(url:string)=>{
      if(url.endsWith("/"+other))return json({...clean,id:other,state:posted?"posted":"staged",message_id:posted?id:null});
      if(url.includes("cursor="))return json(batch([{...clean,id:other}]));
      return json({...batch([clean]),next_cursor:id});
    });vi.stubGlobal("fetch",mock);let view!:ReturnType<typeof render>;await act(async()=>{view=render(<Harness/>);});
    await act(async()=>{fireEvent.click(screen.getByRole("button",{name:"Load more files"}));});
    fireEvent.click(screen.getByLabelText("Attach this clean file 2"));expect(screen.getByTestId("selection").textContent).toBe(other);
    posted=true;await act(async()=>{view.rerender(<Harness revision={1}/>);});
    expect(mock.mock.calls.some(call=>call[0]===base+"/files/"+other)).toBe(true);expect(screen.getByTestId("selection").textContent).toBe("");
    expect(screen.queryByLabelText("Attach this clean file 2")).toBeNull();
  });
  it("renders posted clean downloads without authoring controls and suppresses staff-only files for owners",()=>{
    const posted={...clean,state:"posted" as const,message_id:other};const {rerender}=render(<PostedHelpdeskFiles files={[posted,{...posted,id:other,internal:true}]} base={base} locale="ta" staff={false}/>);
    expect(screen.getAllByRole("link")).toHaveLength(1);expect(screen.getByRole("link").getAttribute("href")).toBe(`${base}/files/${id}/content`);expect(screen.queryByRole("button")).toBeNull();
    rerender(<PostedHelpdeskFiles files={[posted,{...posted,id:other,internal:true}]} base={base} locale="en" staff/>);expect(screen.getAllByRole("link")).toHaveLength(2);
    rerender(<PostedHelpdeskFiles files={[{...posted,usable:false}]} base={base} locale="en" staff/>);expect(screen.queryByRole("link")).toBeNull();expect(screen.getByText(/unavailable for download/)).toBeTruthy();
  });
});
