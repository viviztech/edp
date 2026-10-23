"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { components } from "../../../../lib/api-contracts";
import { DefinitionDetails, impactMutation, words, type Definition, type Locale } from "../../impact/content";

type Create = components["schemas"]["ImpactDefinitionCreate"];
const empty = (): Create => ({ title_en: "", title_ta: "", definition_en: "", definition_ta: "", reason: "" });
function Edition({ item, locale, disabled, command }: { item: Definition; locale: Locale; disabled: boolean;
  command: (item: Definition, action: "publish" | "archive", reason: string) => Promise<boolean> }) {
  const t = words[locale]; const [reason, setReason] = useState("");
  useEffect(() => { const warn = (event: BeforeUnloadEvent) => { if (reason.trim()) event.preventDefault(); }; window.addEventListener("beforeunload", warn); return () => window.removeEventListener("beforeunload", warn); }, [reason]);
  return <article className="impact-panel"><DefinitionDetails definition={item} locale={locale} /><small>{t.revision} {item.version} · {new Date(item.created_at).toLocaleString(locale)}</small>
    {item.state !== "archived" && <form aria-label={`${t.definition} ${item.edition}`} onSubmit={(event) => { event.preventDefault(); void command(item, item.state === "draft" ? "publish" : "archive", reason).then((ok) => { if (ok) setReason(""); }); }}>
      <label>{t.definitionReason}<textarea required minLength={3} maxLength={500} disabled={disabled} value={reason} onChange={(event) => setReason(event.target.value)} /></label>
      <button disabled={disabled || reason.trim().length < 3}>{item.state === "draft" ? t.publish : t.archive}</button></form>}
  </article>;
}

export default function Definitions({ org, locale }: { org: string; locale: Locale }) {
  const t = words[locale]; const base = `/api/impact/organizations/${org}/definitions`;
  const [items, setItems] = useState<Definition[]>([]); const [cursor, setCursor] = useState<string | null>(null);
  const [draft, setDraft] = useState<Create>(empty); const [busy, setBusy] = useState(false); const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState(""); const [blocked, setBlocked] = useState(false); const [failed, setFailed] = useState(false);
  const mounted = useRef(true); const lock = useRef(false); const generation = useRef(0);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; generation.current += 1; }; }, []);
  useEffect(() => { const warn = (event: BeforeUnloadEvent) => { if (Object.values(draft).some((value) => value.trim())) event.preventDefault(); }; window.addEventListener("beforeunload", warn); return () => window.removeEventListener("beforeunload", warn); }, [draft]);
  const load = useCallback(async (next?: string) => {
    const attempt = ++generation.current;
    try { const response = await fetch(`${base}?limit=25${next ? `&cursor=${next}` : ""}`, { cache: "no-store" }); if (!response.ok) throw new Error();
      const batch = await response.json() as components["schemas"]["ImpactDefinitionList"];
      if (mounted.current && generation.current === attempt) { setItems((old) => { const latest = new Map(old.map((item) => [item.id, item])); for (const item of batch.items) latest.set(item.id, item); return [...latest.values()]; }); setCursor(batch.next_cursor); setFailed(false); setBlocked(false); }
    } catch { if (mounted.current && generation.current === attempt) { setMessage(t.error); setFailed(true); } }
    finally { if (mounted.current && generation.current === attempt) setLoading(false); }
  }, [base, t.error]);
  useEffect(() => { void Promise.resolve().then(() => load()); }, [load]);
  async function write(body: Create | components["schemas"]["ImpactDefinitionCommand"], path = "") {
    if (lock.current || blocked) return false; lock.current = true; setBusy(true); setMessage("");
    try { const response = await impactMutation(`${base}${path}`, body);
      if (!response.ok) { if (mounted.current) { setBlocked(response.status === 409 || response.status >= 500); setMessage(response.status === 409 ? t.conflict : response.status === 403 ? t.access : t.error); } return false; }
      const item = await response.json() as Definition;
      if (mounted.current) { setItems((old) => old.some((entry) => entry.id === item.id) ? old.map((entry) => entry.id === item.id ? item : entry) : [item, ...old]); if (!path) setDraft(empty()); setMessage(t.done); } return true;
    } catch { if (mounted.current) { setBlocked(true); setMessage(t.uncertain); } return false; }
    finally { lock.current = false; if (mounted.current) setBusy(false); }
  }
  return <section aria-label={t.definitions}><h2>{t.definitions}</h2><p>{t.definitionIntro}</p>
    <p role="status">{loading ? t.loading : message}</p>{(blocked || failed) && <button disabled={busy || loading} onClick={() => { setLoading(true); void load(); }}>{t.refreshDefinitions}</button>}
    <form aria-label={t.createDefinition} className="impact-panel" onSubmit={(event) => { event.preventDefault(); void write(draft); }}><h3>{t.createDefinition}</h3><fieldset disabled={busy || loading || blocked}>
      {([ ["title_en", t.titleEn], ["title_ta", t.titleTa], ["definition_en", t.definitionEn], ["definition_ta", t.definitionTa], ["reason", t.definitionReason] ] as [keyof Create, string][]).map(([field, label]) => <label key={field}>{label}
        {field.startsWith("title_") ? <input name={field} required minLength={3} maxLength={200} value={draft[field]} onChange={(event) => setDraft((old) => ({ ...old, [field]: event.target.value }))} />
          : <textarea name={field} required minLength={3} maxLength={field === "reason" ? 500 : 5000} value={draft[field]} onChange={(event) => setDraft((old) => ({ ...old, [field]: event.target.value }))} />}</label>)}
      <button disabled={Object.values(draft).some((value) => value.trim().length < 3)}>{t.createDefinition}</button></fieldset></form>
    {!loading && !items.length && <p>{t.noDefinitions}</p>}
    {items.map((item) => <Edition key={item.id} item={item} locale={locale} disabled={busy || loading || blocked}
      command={(edition, action, reason) => write({ expected_version: edition.version, reason: reason.trim() }, `/${edition.id}/${action}`)} />)}
    {cursor && <button disabled={busy || loading || blocked} onClick={() => { setLoading(true); void load(cursor); }}>{t.more}</button>}
  </section>;
}
