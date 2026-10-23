"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { components } from "../../../../lib/api-contracts";
import { FundingHistory, ResourceCard, statusLabel, words, type Locale, type Resource } from "../../knowledge/content";
import { knowledgeMutation } from "../../knowledge/view";

type Draft = components["schemas"]["KnowledgeCreate"];
type Batch = components["schemas"]["KnowledgeList"];
type Cases = components["schemas"]["FundingCaseList"];
type History = components["schemas"]["KnowledgeHistory"];
const staffWords = {
  en: { title: "Resource publishing and funding", editor: "Resource editor", new: "New resource", create: "Create draft", save: "Save draft",
    edit: "Edit resource", publish: "Publish resource", draft: "Return to draft", archive: "Archive resource", slug: "Slug", titleField: "Title",
    language: "Language", visibility: "Visibility", public: "Public", participants: "Participants", tags: "Tags (comma separated)",
    documents: "Required documents (one per line)", url: "Official source URL", min: "Official minimum", max: "Official maximum",
    reason: "Reason for change", history: "Resource history", queue: "Participant funding cases", participant: "Participant reference",
    discard: "Discard your unsaved resource edits?", readonly: "Return this resource to draft before editing its content.",
    revision: "Version", draftState: "Draft", published: "Published", archived: "Archived", none: "No funding cases in this organization.",
    created: "Created", updated: "Updated", recorded: "Recorded change",
    hint: "Publish each language separately. Enter only amounts supplied by the official provider.",
    saveFirst: "Save your content edits before changing publication status.",
    refresh: "Refresh saved resource", latest: "Latest saved resource",
  },
  ta: { title: "வள வெளியீடும் நிதிப் பதிவுகளும்", editor: "வளத் திருத்தி", new: "புதிய வளம்", create: "வரைவை உருவாக்கு", save: "வரைவைச் சேமி",
    edit: "வளத்தைத் திருத்து", publish: "வளத்தை வெளியிடு", draft: "வரைவுக்குத் திரும்பு", archive: "வளத்தைக் காப்பகப்படுத்து", slug: "இணைப்புச் சொல்", titleField: "தலைப்பு",
    language: "மொழி", visibility: "காட்சியளிப்பு", public: "பொது", participants: "பங்கேற்பாளர்கள்", tags: "குறிச்சொற்கள் (காற்புள்ளியால் பிரிக்கவும்)",
    documents: "தேவையான ஆவணங்கள் (ஒரு வரிக்கு ஒன்று)", url: "அதிகாரப்பூர்வ ஆதார இணைய முகவரி", min: "அதிகாரப்பூர்வ குறைந்தபட்சத் தொகை", max: "அதிகாரப்பூர்வ அதிகபட்சத் தொகை",
    reason: "மாற்றத்திற்கான காரணம்", history: "வள வரலாறு", queue: "பங்கேற்பாளர் நிதிப் பதிவுகள்", participant: "பங்கேற்பாளர் குறிப்பு",
    discard: "சேமிக்காத வளத் திருத்தங்களை நீக்கவா?", readonly: "உள்ளடக்கத்தைத் திருத்த இந்த வளத்தை வரைவுக்குத் திருப்பவும்.",
    revision: "பதிப்பு", draftState: "வரைவு", published: "வெளியிடப்பட்டது", archived: "காப்பகம்", none: "இந்த அமைப்பில் நிதிப் பதிவுகள் இல்லை.",
    created: "உருவாக்கப்பட்டது", updated: "புதுப்பிக்கப்பட்டது", recorded: "பதிவான மாற்றம்",
    hint: "ஒவ்வொரு மொழியையும் தனியாக வெளியிடுங்கள். அதிகாரப்பூர்வ வழங்குநர் கூறிய தொகைகளை மட்டும் உள்ளிடுங்கள்.",
    saveFirst: "வெளியீட்டு நிலையை மாற்றும் முன் உள்ளடக்கத் திருத்தங்களைச் சேமிக்கவும்.",
    refresh: "சேமித்த வளத்தைப் புதுப்பி", latest: "அண்மையில் சேமித்த வளம்",
  },
} as const;

function emptyDraft(locale: Locale): Draft {
  return { kind: "scheme", locale, slug: "", title: "", provider: "", type: "", description: "", eligibility: "", benefits: "",
    sector: "", geography: "", tags: [], application_process: "", documents: [], official_url: "", opens_on: null, closes_on: null,
    last_verified_at: new Date().toISOString().slice(0, 10), visibility: "public", contact: "", funding_amount_min: null,
    funding_amount_max: null, currency: "INR" };
}

// Whitelist editable properties: immutable evidence and response metadata never become request fields.
function writable(item: Draft): Draft {
  return { kind: item.kind, locale: item.locale, slug: item.slug, title: item.title, provider: item.provider, type: item.type,
    description: item.description, eligibility: item.eligibility, benefits: item.benefits ?? "", sector: item.sector, geography: item.geography,
    tags: item.tags ?? [], application_process: item.application_process, documents: item.documents ?? [], official_url: item.official_url,
    opens_on: item.opens_on ?? null, closes_on: item.closes_on ?? null, last_verified_at: item.last_verified_at,
    visibility: item.visibility ?? "public", contact: item.contact ?? "", funding_amount_min: item.funding_amount_min ?? null,
    funding_amount_max: item.funding_amount_max ?? null, currency: "INR" };
}

function ResourceEditor({ item, locale, busy, onDirty, submit }: { item: Resource | null; locale: Locale; busy: boolean;
  onDirty: (dirty: boolean) => void;
  submit: (fields: Draft, reason: string, action: "save" | "publish" | "draft" | "archive") => Promise<void> }) {
  const t = words[locale]; const s = staffWords[locale];
  const [fields, setFields] = useState<Draft>(() => writable(item ?? emptyDraft(locale)));
  const [tags, setTags] = useState((fields.tags ?? []).join(", "));
  const [documents, setDocuments] = useState((fields.documents ?? []).join("\n"));
  const [reason, setReason] = useState(""); const editable = !item || item.state === "draft";
  const [contentDirty, setContentDirty] = useState(false);
  function set<Key extends keyof Draft>(key: Key, value: Draft[Key]) { setFields((old) => ({ ...old, [key]: value })); setContentDirty(true); onDirty(true); }
  const textFields = [["title", s.titleField, 200], ["provider", t.provider, 200], ["type", t.type, 120],
    ["sector", t.sector, 120], ["geography", t.geography, 120]] as const;
  const proseFields = [["description", t.description, 10000], ["eligibility", t.eligibility, 5000],
    ["benefits", t.benefits, 5000], ["application_process", t.process, 5000]] as const;
  return <section className="program-panel"><h2>{s.editor}</h2><p>{s.hint}</p>
    {item && <p>{s.revision} {item.version} · {item.state === "draft" ? s.draftState : s[item.state]}</p>}
    {!editable && <p>{s.readonly}</p>}
    <form aria-label={s.editor} onSubmit={(event) => { event.preventDefault();
      void submit({ ...writable(fields), tags: tags.split(",").map((value) => value.trim()).filter(Boolean),
        documents: documents.split("\n").map((value) => value.trim()).filter(Boolean) }, reason, "save");
    }}><fieldset disabled={busy || !editable} style={{ border: 0, padding: 0, minWidth: 0 }}>
      <div className="program-grid"><label>{t.kind}<select name="kind" disabled={!!item} value={fields.kind} onChange={(event) => {
        set("kind", event.target.value as Draft["kind"]);
        if (event.target.value !== "funding") { set("funding_amount_min", null); set("funding_amount_max", null); }
      }}>
        {(["scheme", "funding", "opportunity"] as const).map((kind) => <option key={kind} value={kind}>{t[kind]}</option>)}
      </select></label><label>{s.language}<select name="locale" disabled={!!item} value={fields.locale} onChange={(event) => set("locale", event.target.value as Locale)}>
        <option value="en">English</option><option value="ta">தமிழ்</option></select></label>
      <label>{s.slug}<input disabled={!!item} required pattern="[a-z0-9]+(-[a-z0-9]+)*" maxLength={120} value={fields.slug} onChange={(event) => set("slug", event.target.value)} /></label>
      {textFields.map(([key, label, max]) => <label key={key}>{label}<input required maxLength={max} value={fields[key]} onChange={(event) => set(key, event.target.value)} /></label>)}
      {proseFields.map(([key, label, max]) => <label key={key}>{label}<textarea required={key !== "benefits"} maxLength={max} value={fields[key] ?? ""} onChange={(event) => set(key, event.target.value)} /></label>)}
      <label>{s.tags}<input maxLength={4020} value={tags} onChange={(event) => { setTags(event.target.value); setContentDirty(true); onDirty(true); }} /></label>
      <label>{s.documents}<textarea maxLength={6030} value={documents} onChange={(event) => { setDocuments(event.target.value); setContentDirty(true); onDirty(true); }} /></label>
      <label>{s.url}<input required type="url" maxLength={2000} value={fields.official_url} onChange={(event) => set("official_url", event.target.value)} /></label>
      <label>{t.opens}<input type="date" value={fields.opens_on ?? ""} onChange={(event) => set("opens_on", event.target.value || null)} /></label>
      <label>{t.closes}<input type="date" min={fields.opens_on ?? undefined} value={fields.closes_on ?? ""} onChange={(event) => set("closes_on", event.target.value || null)} /></label>
      <label>{t.verified}<input required type="date" max={new Date().toISOString().slice(0, 10)} value={fields.last_verified_at} onChange={(event) => set("last_verified_at", event.target.value)} /></label>
      <label>{s.visibility}<select name="visibility" value={fields.visibility} onChange={(event) => set("visibility", event.target.value as Draft["visibility"])}>
        <option value="public">{s.public}</option><option value="participants">{s.participants}</option></select></label>
      <label>{t.contact}<input maxLength={1000} value={fields.contact ?? ""} onChange={(event) => set("contact", event.target.value)} /></label>
      {fields.kind === "funding" && ([ ["funding_amount_min", s.min], ["funding_amount_max", s.max] ] as const).map(([key, label]) =>
        <label key={key}>{label}<input type="number" min="0" step="0.01" value={fields[key] ?? ""} onChange={(event) => set(key, event.target.value || null)} /></label>)}
      </div></fieldset>
      {item && <label>{s.reason}<textarea required maxLength={500} value={reason} disabled={busy} onChange={(event) => { setReason(event.target.value); onDirty(true); }} /></label>}
      {editable && <p><button disabled={busy || (!!item && !reason.trim())}>{item ? s.save : s.create}</button></p>}
    </form>
    {item && contentDirty && <p>{s.saveFirst}</p>}
    {item && <p>{item.state === "draft" ? <button disabled={busy || contentDirty || !reason.trim()} onClick={() => void submit(fields, reason, "publish")}>{s.publish}</button>
      : <button disabled={busy || contentDirty || !reason.trim()} onClick={() => void submit(fields, reason, "draft")}>{s.draft}</button>}{" "}
      {item.state !== "archived" && <button disabled={busy || contentDirty || !reason.trim()} onClick={() => void submit(fields, reason, "archive")}>{s.archive}</button>}</p>}
  </section>;
}

export default function KnowledgeStaff({ org, locale, canManage, canFunding }: { org: string; locale: Locale; canManage: boolean; canFunding: boolean }) {
  const t = words[locale]; const s = staffWords[locale]; const base = `/api/knowledge/organizations/${org}`;
  const actionLabels: Record<string, string> = { created: s.created, updated: s.updated, published: s.published, draft: s.draftState, archived: s.archived };
  const [items, setItems] = useState<Resource[]>([]); const [cursor, setCursor] = useState<string | null>(null);
  const [cases, setCases] = useState<Cases>({ items: [], next_cursor: null });
  const [selected, setSelected] = useState<Resource | null>(null); const [editorKey, setEditorKey] = useState(0);
  const [history, setHistory] = useState<History | null>(null); const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false); const [loading, setLoading] = useState(true); const [message, setMessage] = useState("");
  const [needsRefresh, setNeedsRefresh] = useState(false); const mutationLock = useRef(false); const selection = useRef(0);
  const active = useRef(true);
  useEffect(() => { active.current = true; return () => { active.current = false; }; }, []);
  useEffect(() => { if (!dirty) return; const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn); return () => window.removeEventListener("beforeunload", warn); }, [dirty]);
  const load = useCallback(() => {
    return Promise.all([
        canManage ? fetch(`${base}/items?locale=${locale}&availability=all&limit=25`, { cache: "no-store" }) : null,
        canFunding ? fetch(`${base}/funding-cases?limit=25`, { cache: "no-store" }) : null,
      ]).then(async ([resources, funding]) => {
      if ((resources && !resources.ok) || (funding && !funding.ok)) throw new Error();
      const batch = resources ? await resources.json() as Batch : null;
      const queue = funding ? await funding.json() as Cases : null;
      if (active.current) { setMessage(""); if (batch) { setItems(batch.items); setCursor(batch.next_cursor); } if (queue) setCases(queue); }
    }).catch(() => { if (active.current) setMessage(t.error); }).finally(() => { if (active.current) setLoading(false); });
  }, [base, canFunding, canManage, locale, t.error]);
  useEffect(() => { void load(); }, [load]);
  async function select(item: Resource | null) {
    if (dirty && !window.confirm(s.discard)) return;
    const generation = ++selection.current;
    setDirty(false); setMessage(""); setSelected(item); setEditorKey((key) => key + 1); setHistory(null);
    if (item) {
      try { const response = await fetch(`${base}/items/${item.id}/history?limit=25`, { cache: "no-store" });
        if (!response.ok) throw new Error(); const data = await response.json() as History;
        if (generation === selection.current) setHistory(data);
      } catch { if (generation === selection.current) setMessage(t.error); }
    }
  }
  async function submit(fields: Draft, reason: string, action: "save" | "publish" | "draft" | "archive") {
    if (mutationLock.current) return; mutationLock.current = true; setBusy(true); setMessage("");
    try {
      const path = selected ? `/items/${selected.id}${action === "save" ? "" : `/${action}`}` : "/items";
      const body = action === "save" ? { ...writable(fields), ...(selected ? { expected_version: selected.version, reason } : {}) }
        : { expected_version: selected?.version, reason };
      const response = await knowledgeMutation(base + path, body, selected && action === "save" ? "PATCH" : "POST");
      if (!response.ok) { setMessage(response.status === 409 ? t.conflict : t.error); setNeedsRefresh(response.status === 409); return; }
      const result = await response.json() as Resource;
      setDirty(false); setNeedsRefresh(false); setSelected(result); setEditorKey((key) => key + 1);
      setItems((old) => [result, ...old.filter((item) => item.id !== result.id)]);
      const evidence = await fetch(`${base}/items/${result.id}/history?limit=25`, { cache: "no-store" });
      if (!evidence.ok) throw new Error(); setHistory(await evidence.json() as History); setMessage(t.done);
    } catch { setMessage(t.error); } finally { mutationLock.current = false; setBusy(false); }
  }
  async function refreshSelected() {
    if (!selected || mutationLock.current) return; mutationLock.current = true; setBusy(true); setMessage("");
    try { const response = await fetch(`${base}/items/${selected.id}`, { cache: "no-store" }); if (!response.ok) throw new Error();
      const latest = await response.json() as Resource; setSelected(latest);
      setItems((old) => old.map((item) => item.id === latest.id ? latest : item)); setNeedsRefresh(false); setMessage(t.refreshed);
    } catch { setMessage(t.error); } finally { mutationLock.current = false; setBusy(false); }
  }
  async function more(which: "resources" | "cases" | "history") {
    const next = which === "resources" ? cursor : which === "cases" ? cases.next_cursor : history?.next_cursor;
    if (!next || busy) return; setBusy(true); setMessage("");
    try {
      const path = which === "resources" ? "items" : which === "cases" ? "funding-cases" : `items/${selected?.id}/history`;
      const response = await fetch(`${base}/${path}?limit=25&cursor=${next}${which === "resources" ? `&locale=${locale}&availability=all` : ""}`, { cache: "no-store" });
      if (!response.ok) throw new Error();
      if (which === "resources") { const batch = await response.json() as Batch; setItems((old) => [...old, ...batch.items]); setCursor(batch.next_cursor); }
      else if (which === "cases") { const batch = await response.json() as Cases; setCases((old) => ({ items: [...old.items, ...batch.items], next_cursor: batch.next_cursor })); }
      else { const batch = await response.json() as History; setHistory((old) => ({ items: [...(old?.items ?? []), ...batch.items], next_cursor: batch.next_cursor })); }
    } catch { setMessage(t.error); } finally { setBusy(false); }
  }
  return <><header className="program-heading"><div><p className="eyebrow">K01</p><h1>{s.title}</h1></div></header>
    <p role="status">{loading ? t.loading : message}</p>
    {message && <button disabled={loading || busy || dirty} onClick={() => { setLoading(true); setMessage(""); void load(); }}>{t.retry}</button>}
    {needsRefresh && <button disabled={loading || busy} onClick={() => void refreshSelected()}>{s.refresh}</button>}
    {canManage && <><p><button disabled={busy || loading} onClick={() => void select(null)}>{s.new}</button></p>
      <ResourceEditor key={editorKey} item={selected} locale={locale} busy={busy || loading} onDirty={setDirty} submit={submit} />
      {selected && <details><summary>{s.latest}</summary><ResourceCard item={selected} locale={locale} /></details>}
      {history && <section className="program-panel"><h2>{s.history}</h2><ol>{history.items.map((event) => <li key={event.id}>
        {s.revision} {event.version} · {actionLabels[event.action] ?? s.recorded} · <time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString(locale)}</time>
        <p style={{ overflowWrap: "anywhere" }}>{event.reason}</p></li>)}</ol>
        {history.next_cursor && <button disabled={busy} onClick={() => void more("history")}>{t.more}</button>}</section>}
      <section aria-label={t.title}>{!loading && !items.length && <p>{t.empty}</p>}{items.map((item) => <ResourceCard key={item.id} item={item} locale={locale}>
        <p>{item.state === "draft" ? s.draftState : s[item.state]} · {s.revision} {item.version}</p>
        <button disabled={busy || loading} onClick={() => void select(item)}>{s.edit}</button></ResourceCard>)}</section>
      {cursor && <button disabled={busy} onClick={() => void more("resources")}>{t.more}</button>}
    </>}
    {canFunding && <section aria-label={s.queue}><h2>{s.queue}</h2><p>{t.reported}</p>
      {!loading && !cases.items.length && <p>{s.none}</p>}{cases.items.map((item) => <article key={item.id} className="program-panel" aria-label={item.item_title}>
        <h3>{item.item_title}</h3><p>{s.participant}: {item.participant_id}</p><p>{t.status}: {statusLabel(item.status, locale)}</p>
        <FundingHistory item={item} locale={locale} /></article>)}
      {cases.next_cursor && <button disabled={busy} onClick={() => void more("cases")}>{t.more}</button>}
    </section>}
  </>;
}
