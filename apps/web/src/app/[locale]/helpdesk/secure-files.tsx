"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import type { components } from "../../../lib/api-contracts";
import type { Locale } from "./content";
import { secureFileWords } from "./secure-files-content";

type Item=components["schemas"]["HelpdeskFileView"];
type Batch=components["schemas"]["HelpdeskFileList"];
type Intent=components["schemas"]["HelpdeskFileIntent"];
type Recovery={file:File;intent:Intent;binding?:Item};
const scanning=(item:Item)=>item.state==="staged"&&["uploading","quarantined","scanning"].includes(item.file.state);

async function token(){const response=await fetch("/api/session/csrf",{cache:"no-store"});if(!response.ok)throw new Error();return (await response.json() as {csrf_token:string}).csrf_token;}
async function mutate(url:string,body:object,method="POST"){return fetch(url,{method,headers:{"Content-Type":"application/json","X-CSRF-Token":await token()},body:JSON.stringify(body)});}

export function PostedHelpdeskFiles({files,base,locale,staff}:{files:Item[];base:string;locale:Locale;staff:boolean}){
  const t=secureFileWords[locale];
  return <>{files.filter(item=>item.state==="posted"&&(!item.internal||staff)).map((item,index)=><p key={item.id}>
    {item.usable?<a href={`${base}/files/${item.id}/content`} download>{t.download} {index+1}</a>:<span>{t.noDownload} {index+1}</span>}
    {` (${item.file.media_type}, ${item.file.byte_size.toLocaleString(locale)} ${t.bytes})`}
  </p>)}</>;
}

export default function SecureHelpdeskFiles({base,locale,internal,disabled,selected,onSelect,onBusy,onDirty,revision}:{
  base:string;locale:Locale;internal:boolean;disabled:boolean;selected:string[];onSelect:(ids:string[])=>void;
  onBusy:(busy:boolean)=>void;onDirty:(dirty:boolean)=>void;revision:number;
}){
  const t=secureFileWords[locale],url=base+"/files";
  const [batch,setBatch]=useState<Batch|null>(null),[busy,setBusy]=useState(false),[loading,setLoading]=useState(true),[message,setMessage]=useState("");
  const [file,setFile]=useState<File|null>(null),[uncertain,setUncertain]=useState(false),[inputKey,setInputKey]=useState(0);
  const locked=useRef(false),recovery=useRef<Recovery|null>(null),polls=useRef(0),selection=useRef(selected);
  const parse=useCallback(async<T,>(response:Response):Promise<T>=>{if(!response.ok)throw new Error(response.status===401||response.status===403?t.access:t.error);return response.json() as Promise<T>;},[t.access,t.error]);
  useEffect(()=>{selection.current=selected;},[selected]);
  const reconcile=useCallback(async(data:Batch,signal?:AbortSignal)=>{
    // Explicit IDs are bounded by MessageCreate, not discovered by an unbounded
    // list scan. Recheck later-page selections after a lost message response.
    const missing=selection.current.filter(id=>!data.items.some(item=>item.id===id)).slice(0,100),extra:Item[]=[];
    for(let offset=0;offset<missing.length;offset+=4){extra.push(...await Promise.all(missing.slice(offset,offset+4).map(id=>fetch(`${url}/${id}`,{cache:"no-store",signal}).then(response=>parse<Item>(response)))));}
    return {...data,items:[...data.items,...extra]};
  },[url,parse]);
  useEffect(()=>{let active=true;const controller=new AbortController();polls.current=0;
    Promise.resolve().then(()=>{if(active)setLoading(true);return fetch(url+"?limit=25",{cache:"no-store",signal:controller.signal});}).then(response=>parse<Batch>(response)).then(data=>reconcile(data,controller.signal)).then(data=>{if(active)setBatch(data);}).catch(()=>{if(active)setMessage(t.error);}).finally(()=>{if(active)setLoading(false);});
    return()=>{active=false;controller.abort();};
  },[url,revision,parse,reconcile,t.error]);
  useEffect(()=>{onDirty(Boolean(file)||uncertain||selected.length>0);},[file,uncertain,selected.length,onDirty]);
  useEffect(()=>{if(!batch)return;const valid=selected.filter(id=>{const item=batch.items.find(row=>row.id===id);return batch.collection_enabled&&(!item||(item.state==="staged"&&item.usable&&item.internal===internal));});
    if(valid.length!==selected.length)onSelect(valid);
  },[batch,selected,internal,onSelect]);
  useEffect(()=>{
    if(!batch||busy||disabled||!batch.items.some(scanning)||polls.current>=10)return;
    const controller=new AbortController();let active=true;
    const timer=setTimeout(()=>{polls.current++;void fetch(url+"?limit=25",{cache:"no-store",signal:controller.signal}).then(response=>parse<Batch>(response)).then(data=>{
      if(!active)return;setBatch(old=>old?{...data,next_cursor:old.next_cursor,items:[...old.items.map(item=>data.items.find(next=>next.id===item.id)??item),...data.items.filter(item=>!old.items.some(oldItem=>oldItem.id===item.id))]}:data);
      if(polls.current>=10&&data.items.some(scanning))setMessage(t.pollStopped);
    }).catch(()=>{if(active)setMessage(t.error);});},2000);
    return()=>{active=false;clearTimeout(timer);controller.abort();};
  },[batch,busy,disabled,url,parse,t.error,t.pollStopped]);
  function accept(item:Item){setBatch(old=>old&&({...old,items:old.items.some(previous=>previous.id===item.id)?old.items.map(previous=>previous.id===item.id?item:previous):[item,...old.items]}));}
  async function run(action:()=>Promise<void>){if(locked.current||disabled)return;locked.current=true;setBusy(true);onBusy(true);setMessage("");
    try{await action();}catch(error){setMessage(error instanceof Error&&[t.error,t.access,t.invalid,t.visibilityHint,t.policyMismatch].includes(error.message as typeof t.error)?error.message:t.error);}finally{locked.current=false;setBusy(false);onBusy(false);}}
  async function refresh(more=false){await run(async()=>{const page=await parse<Batch>(await fetch(url+(more&&batch?.next_cursor?`?limit=25&cursor=${batch.next_cursor}`:"?limit=25"),{cache:"no-store"}));const data=more?page:await reconcile(page);
    setBatch(old=>more&&old?{...data,items:[...old.items,...data.items.filter(item=>!old.items.some(previous=>previous.id===item.id))]}:data);polls.current=0;});}
  async function upload(){await run(async()=>{
    if(!file||!batch?.collection_enabled)throw new Error(t.invalid);
    let saved=recovery.current;
    if(saved&&saved.intent.internal!==internal)throw new Error(t.visibilityHint);
    if(!saved){const policy=batch.policy;if(!policy||!policy.allowed_mime_types.includes(file.type as Intent["media_type"])||!file.size||file.size>Math.min(policy.max_upload_bytes,batch.max_upload_bytes))throw new Error(t.invalid);
      const digest=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",await file.arrayBuffer())),byte=>byte.toString(16).padStart(2,"0")).join("");
      saved={file,intent:{client_request_id:crypto.randomUUID(),policy_id:policy.id,internal,media_type:file.type as Intent["media_type"],byte_size:file.size,sha256:digest}};recovery.current=saved;
    }
    setUncertain(true);
    if(!saved.binding){saved.binding=await parse<Item>(await mutate(url,saved.intent));accept(saved.binding);}
    let current=await parse<Item>(await fetch(`${url}/${saved.binding.id}`,{cache:"no-store"}));saved.binding=current;accept(current);
    if(current.state!=="staged")throw new Error(t.error);
    if(["pending","uploading"].includes(current.file.state)){
      current=await parse<Item>(await fetch(`${url}/${current.id}/content`,{method:"PUT",headers:{"Content-Type":saved.intent.media_type,"If-Match":`"${current.file.version}"`,"X-CSRF-Token":await token()},body:saved.file}));saved.binding=current;accept(current);
    }
    if(["infected","rejected","deleted"].includes(current.file.state)||(current.file.state==="clean"&&!current.usable))throw new Error(t.error);
    recovery.current=null;setFile(null);setInputKey(old=>old+1);setUncertain(false);polls.current=0;setMessage(current.usable?t.ready:t.scanWait);
  });}
  async function remove(item:Item){await run(async()=>{const result=await parse<Item>(await mutate(`${url}/${item.id}`,{expected_version:item.version},"DELETE"));accept(result);onSelect(selected.filter(id=>id!==item.id));
    if(recovery.current?.binding?.id===item.id){recovery.current=null;setFile(null);setUncertain(false);setInputKey(old=>old+1);}});}
  function choose(item:Item,checked:boolean){if(!checked){onSelect(selected.filter(id=>id!==item.id));return;}
    const existing=batch?.items.find(row=>selected.includes(row.id));if(existing&&existing.policy.id!==item.policy.id){setMessage(t.policyMismatch);return;}
    if(selected.length>=item.policy.max_files){setMessage(t.invalid);return;}
    if(item.usable&&item.state==="staged"&&item.internal===internal)onSelect([...selected,item.id]);}
  const blocked=disabled||busy||loading,staged=batch?.items.filter(item=>item.state==="staged")??[];
  const label=(value:string)=>t[value as keyof typeof t]??value;
  return <section className="helpdesk-panel" aria-label={t.title} aria-busy={busy||loading}><h3>{t.title}</h3><p>{t.privateHint}</p><p role="status">{loading?t.loading:message}</p>
    {batch?.policy&&<><h4>{t.policy}: {batch.policy.name} ({batch.policy.edition})</h4><p>{t.notice}: {locale==="ta"?batch.policy.notice_ta:batch.policy.notice_en}</p><p>{t.limit}: {Math.min(batch.policy.max_upload_bytes,batch.max_upload_bytes).toLocaleString(locale)} · {t.count}: {batch.policy.max_files} · {t.retention}: {batch.policy.retention_days}</p></>}
    {(!batch?.collection_enabled||!batch.policy)&&<p>{t.disabled}</p>}
    <p>{t.audience}: {internal?t.internal:t.shared}</p><label>{t.select}<input key={inputKey} type="file" accept={batch?.policy?.allowed_mime_types.join(",")??""} disabled={blocked||uncertain||!batch?.collection_enabled||!batch.policy} onChange={event=>{setFile(event.target.files?.[0]??null);recovery.current=null;setMessage("");}}/></label>
    {file&&<p>{file.name} ({file.size.toLocaleString(locale)} {t.bytes})</p>}
    <button type="button" disabled={blocked||!file||!batch?.collection_enabled||(!batch.policy&&!uncertain)} onClick={()=>void upload()}>{uncertain?t.retry:t.upload}</button>
    {(file||uncertain)&&<button type="button" disabled={blocked} onClick={()=>{recovery.current=null;setFile(null);setUncertain(false);setInputKey(old=>old+1);}}>{t.clear}</button>}
    <button type="button" disabled={blocked} onClick={()=>void refresh()}>{t.refresh}</button>{!loading&&!staged.length&&<p>{t.empty}</p>}
    <ul>{staged.map((item,index)=><li key={item.id}><p>{t.file} {index+1}: {item.file.media_type}, {item.file.byte_size.toLocaleString(locale)} {t.bytes} — {label(item.file.state)} · {item.internal?t.internal:t.shared}</p>
      {item.file.failure_code==="scan_unavailable"&&<p>{t.scanUnavailable}</p>}
      <details><summary>{t.policy}: {item.policy.name} ({item.policy.edition})</summary><p>{locale==="ta"?item.policy.notice_ta:item.policy.notice_en}</p><p>{t.retention}: {item.policy.retention_days}</p></details>
      <label className="helpdesk-check"><input type="checkbox" checked={selected.includes(item.id)} disabled={blocked||!batch?.collection_enabled||!item.usable||item.internal!==internal} onChange={event=>choose(item,event.target.checked)}/>{t.use} {index+1}</label>
      <button type="button" disabled={blocked} onClick={()=>void remove(item)}>{t.remove} {index+1}</button>
    </li>)}</ul>
    {batch?.next_cursor&&<button type="button" disabled={blocked} onClick={()=>void refresh(true)}>{t.more}</button>}
  </section>;
}
