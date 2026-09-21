"use client";
import { useEffect, useState } from "react";
import { Button } from "../../../../components/ui/button";
import { Input } from "../../../../components/ui/input";
import { Textarea } from "../../../../components/ui/textarea";
import type { components } from "../../../../lib/api-contracts";
import { cmsMessages } from "../../../../lib/cms-messages";
type Page=components["schemas"]["PageView"];
type Draft=Pick<components["schemas"]["Edit"],"title"|"body"|"seo_title"|"seo_description">;
const empty:Draft={title:"",body:"",seo_title:"",seo_description:""};
export default function Editor({org,permissions,locale}:{org:string;permissions:string[];locale:"en"|"ta"}) {
 const t=cmsMessages[locale], base=`/api/cms/organizations/${org}/pages`;
 const [items,setItems]=useState<Page[]>([]),[cursor,setCursor]=useState<string|null>(null),[selected,setSelected]=useState<Page|null>(null);
 const [language,setLanguage]=useState<"en"|"ta">(locale),[form,setForm]=useState<Draft>(empty),[slug,setSlug]=useState("");
 const [busy,setBusy]=useState(false),[message,setMessage]=useState(""),[reason,setReason]=useState("");
 const [preview,setPreview]=useState<Draft|null>(null),[history,setHistory]=useState<components["schemas"]["History"]|null>(null);
 const current=selected?.translations.find(x=>x.locale===language);
 const allowed=(action:string)=>permissions.includes("cms.page."+action);
 async function api(path:string, method="GET", data?:unknown) {
  const headers:Record<string,string>={"Content-Type":"application/json"};
  if(method!=="GET") {const r=await fetch("/api/session/csrf",{cache:"no-store"}); if(!r.ok) throw new Error(t.error); headers["x-csrf-token"]=(await r.json()).csrf_token;}
  const response=await fetch(path,{method,headers,body:data?JSON.stringify(data):undefined,cache:"no-store"});
  if(!response.ok) throw new Error(response.status===409?t.conflict:t.error);
  return response.json();
 }
 useEffect(()=>{let active=true; fetch(base,{cache:"no-store"}).then(async r=>{if(!r.ok) throw new Error();return r.json();}).then(data=>{if(active){setItems(data.items);setCursor(data.next_cursor);}}).catch(()=>{if(active)setMessage(t.error);});return ()=>{active=false;};},[base,t.error]);
 async function run(work:()=>Promise<void>) {setBusy(true);setMessage("");try{await work();}catch(e){setMessage(e instanceof Error?e.message:t.error);}finally{setBusy(false);}}
 function choose(page:Page|null, lang=language) {setSelected(page);setLanguage(lang); const value=page?.translations.find(x=>x.locale===lang);setForm(value??empty);setSlug(page?.slug??"");setPreview(null);setHistory(null);setReason("");setMessage("");}
 function saved(page:Page){choose(page);setItems(old=>[page,...old.filter(x=>x.id!==page.id)]);setMessage(t.saved);}
 const path=selected?`${base}/${selected.id}/translations/${language}`:"";
 async function load(more=false){const data=await api(base+(more&&cursor?`?cursor=${cursor}`:""));setItems(old=>more?[...old,...data.items]:data.items);setCursor(data.next_cursor);}
 return <div className="cms-grid" aria-busy={busy}>
 <aside><div className="actions"><button disabled={busy||!allowed("create")} onClick={()=>choose(null)}>{t.newPage}</button><button disabled={busy} onClick={()=>run(()=>load())}>{t.retry}</button></div>
 {!items.length&&<p>{t.empty}</p>}<ul>{items.map(p=><li key={p.id}><button disabled={busy} aria-pressed={p.id===selected?.id} onClick={()=>run(async()=>choose(await api(`${base}/${p.id}`)))}>{p.slug}</button></li>)}</ul>{cursor&&<button disabled={busy} onClick={()=>run(()=>load(true))}>{t.more}</button>}</aside>
 <section><p role="status">{busy?t.loading:message}</p><p>{t.note}</p>
 <label>{t.locale}<select value={language} disabled={busy} onChange={e=>choose(selected,e.target.value as "en"|"ta")}><option value="en">English</option><option value="ta">Tamil</option></select></label>
 {current&&<p className="cms-state">{t[current.state]} / v{current.version}</p>}
 <form className="account-form cms-editor-form" onSubmit={e=>{e.preventDefault();run(async()=>{const data=!selected?await api(base,"POST",{...form,slug,locale:language}):!current?await api(`${base}/${selected.id}/translations`,"POST",{...form,locale:language}):await api(path,"PATCH",{title:form.title,body:form.body,seo_title:form.seo_title,seo_description:form.seo_description,expected_version:current.version});saved(data);});}}>
 <fieldset disabled={busy||current?.state==="archived"||!allowed(selected?"update":"create")}>
 <label>{t.slug}<Input required pattern="[a-z0-9]+(-[a-z0-9]+)*" maxLength={120} value={slug} disabled={!!selected} onChange={e=>setSlug(e.target.value)}/></label>
 {(["title","body","seo_title","seo_description"] as const).map(key=><label key={key}>{t[key]}{key==="body"?<Textarea aria-label={t.body} required rows={12} maxLength={50000} value={form[key]} onChange={e=>setForm({...form,[key]:e.target.value})}/>:<Input required={key==="title"} maxLength={key==="seo_title"?70:200} value={form[key]??""} onChange={e=>setForm({...form,[key]:e.target.value})}/>}</label>)}
 <Button type="submit">{selected&&!current?t.addLocale:t.save}</Button></fieldset></form>
 {current&&<><div className="actions"><button disabled={busy} onClick={()=>run(async()=>{const page:Page=await api(path+"/preview");setPreview(page.translations.find(x=>x.locale===language)??null);})}>{t.preview}</button>
 <button disabled={busy||!allowed("publish")||current.state==="archived"} onClick={()=>run(async()=>saved(await api(path+"/publish","POST",{expected_version:current.version})))}>{t.publish}</button>
 <button disabled={busy} onClick={()=>run(async()=>setHistory(await api(path+"/revisions")))}>{t.history}</button>
 {current.state==="archived"&&<button disabled={busy||!allowed("update")} onClick={()=>run(async()=>saved(await api(path+"/restore","POST",{expected_version:current.version})))}>{t.restore}</button>}</div>
 {current.state!=="archived"&&allowed("archive")&&<div className="actions"><label>{t.reason}<input maxLength={500} value={reason} onChange={e=>setReason(e.target.value)}/></label><button disabled={busy||!reason.trim()} onClick={()=>run(async()=>saved(await api(path+"/archive","POST",{expected_version:current.version,reason})))}>{t.archive}</button></div>}
 {preview&&<article className="cms-preview"><h2>{preview.title}</h2><div className="cms-body">{preview.body}</div><button onClick={()=>setPreview(null)}>{t.close}</button></article>}
 {history&&<section><h2>{t.history}</h2>{history.items.map(item=><article key={item.revision_id}><time>{item.published_at}</time><h3>{item.title}</h3><div className="cms-body">{item.body}</div></article>)}{history.next_cursor&&<button disabled={busy} onClick={()=>run(async()=>{const next=await api(path+"/revisions?cursor="+history.next_cursor);setHistory({items:[...history.items,...next.items],next_cursor:next.next_cursor});})}>{t.more}</button>}</section>}</>}
 </section></div>;
}
