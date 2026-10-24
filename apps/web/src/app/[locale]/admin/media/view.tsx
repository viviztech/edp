"use client";
import { useEffect, useRef, useState } from "react";
import type { components } from "../../../../lib/api-contracts";
import { mediaAdminMessages } from "../../../../lib/media-admin-messages";
import type { Locale } from "../../../../lib/messages";

type Asset = components["schemas"]["AssetView"];
type Batch = components["schemas"]["AssetList"];
type Policy = components["schemas"]["AssetPolicy"];
async function csrf(): Promise<string> {
  const result = await fetch("/api/session/csrf", {cache:"no-store"});
  if (!result.ok) throw new Error();
  const value: unknown = (await result.json()).csrf_token;
  if (typeof value !== "string" || !value || value.length > 128) throw new Error();
  return value;
}
const headers = async () => ({"Content-Type":"application/json", "X-CSRF-Token":await csrf()});
type Recovery = {file: File; title: string; metadataId: string; sourceId: string; asset?: Asset};

export default function MediaMetadata({ org, locale, permissions = [] }: { org: string; locale: Locale; permissions?: string[] }) {
  const text = mediaAdminMessages[locale], base = `/api/cms/organizations/${org}/assets`;
  const [items,setItems] = useState<Asset[]>([]), [cursor,setCursor] = useState<string|null>(null), [selected,setSelected] = useState<Asset|null>(null);
  const [policy,setPolicy] = useState<Policy|null>(null), [busy,setBusy] = useState(true), [message,setMessage] = useState("");
  const [title,setTitle] = useState(""), [file,setFile] = useState<File|null>(null), [reason,setReason] = useState("");
  const [fileInputKey,setFileInputKey] = useState(0);
  const [uncertain,setUncertain] = useState(false);
  const locked=useRef(false), recovery=useRef<Recovery|null>(null);
  const canCreate=permissions.includes("cms.asset.create"), canPublish=permissions.includes("cms.asset.publish");
  useEffect(() => {
    let active=true;
    Promise.all([fetch(base,{cache:"no-store"}),fetch(base+"/policy",{cache:"no-store"})]).then(async ([list,rules]) => {
      if(!list.ok || !rules.ok) throw new Error();
      const [batch,configuration]=await Promise.all([list.json() as Promise<Batch>,rules.json() as Promise<Policy>]);
      if(active){setItems(batch.items);setCursor(batch.next_cursor);setPolicy(configuration);}
    }).catch(()=>{if(active)setMessage(text.error);}).finally(()=>{if(active)setBusy(false);});
    return()=>{active=false;};
  },[base,text.error]);
  function accept(a: Asset){setSelected(a);setItems(old=>old.some(item=>item.id===a.id)?old.map(item=>item.id===a.id?a:item):[a,...old]);}
  async function response<T>(result: Response):Promise<T>{
    if(!result.ok){let code="";try{code=(await result.json()).error?.code??"";}catch{}
      throw new Error(code==="version_conflict"?text.stale:code==="asset_policy_retired"?text.retired:text.error);}
    return result.json() as Promise<T>;
  }
  async function run(action:()=>Promise<void>){if(locked.current || busy)return;locked.current=true;setBusy(true);setMessage("");try{await action();}catch(error){setMessage(error instanceof Error&&error.message?error.message:text.error);}finally{locked.current=false;setBusy(false);}}
  async function refresh(more=false){await run(async()=>{const batch=await response<Batch>(await fetch(base+(more&&cursor?`?${new URLSearchParams({cursor})}`:""),{cache:"no-store"}));setItems(old=>more?[...old,...batch.items.filter(item=>!old.some(previous=>previous.id===item.id))]:batch.items);setCursor(batch.next_cursor);});}
  async function inspect(id:string){await run(async()=>{accept(await response<Asset>(await fetch(base+"/"+id,{cache:"no-store"})));});}
  async function upload(){await run(async()=>{
    if(!policy?.enabled || !policy.policy || !file || !title.trim()) {setMessage(text.invalid);return;}
    const rules=policy.policy;
    if(!rules.allowed_mime_types.includes(file.type as typeof rules.allowed_mime_types[number]) || !["application/pdf","image/png","image/jpeg","image/webp"].includes(file.type) || file.size<1 || file.size>Math.min(rules.max_file_bytes,policy.max_upload_bytes) || (file.type!=="application/pdf"&&rules.max_files<2)){setMessage(text.invalid);return;}
    const saved=recovery.current??{file,title:title.trim(),metadataId:crypto.randomUUID(),sourceId:crypto.randomUUID()};recovery.current=saved;
    setUncertain(true);
    let a=saved.asset;
    if(!a){a=await response<Asset>(await fetch(base,{method:"POST",headers:await headers(),body:JSON.stringify({filename:saved.file.name,title:saved.title,media_type:saved.file.type,byte_size:saved.file.size,client_request_id:saved.metadataId})}));saved.asset=a;accept(a);}
    if(!a.source){const digest=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",await saved.file.arrayBuffer())),byte=>byte.toString(16).padStart(2,"0")).join("");
      a=await response<Asset>(await fetch(base+"/"+a.id+"/source",{method:"POST",headers:await headers(),body:JSON.stringify({expected_version:a.version,client_request_id:saved.sourceId,policy_id:rules.id,media_type:saved.file.type,byte_size:saved.file.size,sha256:digest})}));saved.asset=a;accept(a);}
    // Reconcile a lost PUT response through the typed detail, never blindly resend it.
    a=await response<Asset>(await fetch(base+"/"+a.id,{cache:"no-store"}));saved.asset=a;accept(a);
    if(a.source && ["pending","uploading"].includes(a.source.state)){
      a=await response<Asset>(await fetch(base+"/"+a.id+"/source/content",{method:"PUT",headers:{"Content-Type":saved.file.type,"If-Match":`"${a.source.version}"`,"X-CSRF-Token":await csrf()},body:saved.file}));saved.asset=a;accept(a);
    }
    if(a.source && ["infected","rejected","deleted"].includes(a.source.state)) throw new Error(text.newSource);
    setUncertain(false);recovery.current=null;setFile(null);setFileInputKey(value=>value+1);setTitle("");setMessage(text.saved);
  });}
  async function command(action:"prepare"|"publish"|"revoke"){if(!selected||!reason.trim())return;await run(async()=>{
    const candidate=action==="prepare"?selected.source:(selected.media_type==="application/pdf"?selected.source:selected.prepared);
    accept(await response<Asset>(await fetch(`${base}/${selected.id}/${action}`,{method:"POST",headers:await headers(),body:JSON.stringify({expected_version:selected.version,expected_file_version:candidate?.version??null,reason:reason.trim()})})));setMessage(text.saved);
  });}
  const state=(value:string)=>text[value as keyof typeof text]??value;
  return <section aria-busy={busy}>
    <p className="notice">{text.boundary}</p><p role="status">{busy?text.loading:message}</p>
    {canCreate && <section aria-label={text.newMedia}><h2>{text.newMedia}</h2>
      {policy?.policy && <><h3>{text.policy}: {policy.policy.name}</h3><p>{text.notice}: {locale==="ta"?policy.policy.notice_ta:policy.policy.notice_en}</p><p>{text.limit}: {Math.min(policy.policy.max_file_bytes,policy.max_upload_bytes).toLocaleString(locale)}</p><p>{text.policyCount}</p></>}
      {!policy?.enabled||!policy.policy?<p>{text.disabled}</p>:null}
      <label>{text.mediaTitle}<input value={title} maxLength={200} disabled={busy||uncertain} onChange={event=>setTitle(event.target.value)}/></label>
      <label>{text.file}<input key={fileInputKey} type="file" accept="application/pdf,image/jpeg,image/png,image/webp" disabled={busy||uncertain} onChange={event=>setFile(event.target.files?.[0]??null)}/></label>
      {file && <p>{file.name} ({file.size.toLocaleString(locale)} {text.size})</p>}
      <button disabled={busy||!policy?.enabled||!policy.policy||!file||!title.trim()} onClick={upload}>{uncertain?text.retry:text.upload}</button>
      {uncertain && <button disabled={busy} onClick={()=>{recovery.current=null;setUncertain(false);setFile(null);setFileInputKey(value=>value+1);setTitle("");}}>{text.newDraft}</button>}
    </section>}
    <button disabled={busy} onClick={()=>refresh()}>{text.refresh}</button>
    {!busy&&!message&&!items.length&&<p>{text.empty}</p>}
    <ul className="media-metadata-list">{items.map(item=><li key={item.id}><h2>{item.title}</h2><dl>
      <dt>{text.filename}</dt><dd>{item.filename}</dd><dt>{text.mediaType}</dt><dd>{item.media_type}</dd><dt>{text.size}</dt><dd>{item.byte_size.toLocaleString(locale)}</dd>
      <dt>{text.scan}</dt><dd>{state(item.scan_status)}</dd><dt>{text.visibility}</dt><dd>{state(item.visibility)}</dd><dt>{text.byteState}</dt><dd>{state(item.byte_state)}</dd>
    </dl><button disabled={busy} onClick={()=>inspect(item.id)}>{text.choose}: {item.title}</button></li>)}</ul>
    {cursor&&<button disabled={busy} onClick={()=>refresh(true)}>{text.more}</button>}
    {selected&&<section aria-label={text.choose}><h2>{selected.title}</h2><p>{text.version}: {selected.version}</p><p>{text.newSource}</p>
      <button disabled={busy} onClick={()=>inspect(selected.id)}>{text.status}</button>
      <p>{text.source}: {state(selected.source?.state??"unbacked")}</p>
      {(selected.source?.failure_code==="scan_unavailable"||selected.prepared?.failure_code==="scan_unavailable")&&<p>{text.scanUnavailable}</p>}
      {selected.media_type!=="application/pdf"&&<p>{text.prepared}: {state(selected.prepared?.state??"pending")}</p>}<p>{text.scanWait}</p>
      {selected.source?.state==="clean"&&<a href={`${base}/${selected.id}/source/content`}>{text.download}</a>}
      {selected.public_url&&<a href={`/api/public-media/organizations/${org}/assets/${selected.id}/content`} target="_blank" rel="noopener noreferrer">{text.openPublic}</a>}
      {(canCreate||canPublish)&&<label>{text.reason}<textarea value={reason} maxLength={500} disabled={busy} onChange={event=>setReason(event.target.value)}/></label>}
      {canCreate&&selected.source?.state==="clean"&&selected.media_type!=="application/pdf"&&selected.visibility!=="public"&&(!selected.prepared||["pending","uploading"].includes(selected.prepared.state))&&<button disabled={busy||!reason.trim()} onClick={()=>command("prepare")}>{text.prepare}</button>}
      {canPublish&&selected.can_publish&&selected.visibility!=="public"&&<button disabled={busy||!reason.trim()} onClick={()=>command("publish")}>{text.publish}</button>}
      {canPublish&&selected.visibility==="public"&&<button disabled={busy||!reason.trim()} onClick={()=>command("revoke")}>{text.revoke}</button>}
    </section>}
  </section>;
}
