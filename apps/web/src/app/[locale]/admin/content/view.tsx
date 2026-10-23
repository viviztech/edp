"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { components } from "../../../../lib/api-contracts";
import { editorialAdminMessages } from "../../../../lib/editorial-admin-messages";
import { editorialLabels } from "../../../../lib/editorial-copy";
import type { Locale } from "../../../../lib/messages";

type Entry = components["schemas"]["EditorialView"];
type Batch = components["schemas"]["EditorialList"];
type Kind = Entry["kind"];
type Draft = { slug: string; title: string; body: string; starts_at: string; ends_at: string; sort_order: number };
type CreateAddress = { kind: Kind; locale: Locale; slug: string };
const empty: Draft = { slug: "", title: "", body: "", starts_at: "", ends_at: "", sort_order: 0 };
const formOf = (entry: Entry | null): Draft => entry ? {
  slug: entry.slug, title: entry.title, body: entry.body,
  starts_at: entry.starts_at ? new Date(entry.starts_at).toISOString().slice(0, 19) : "",
  ends_at: entry.ends_at ? new Date(entry.ends_at).toISOString().slice(0, 19) : "", sort_order: entry.sort_order ?? 0,
} : { ...empty };
class RequestError extends Error { constructor(public status: number, public code = "request_failed") { super(code); } }

export default function EditorialWorkspace({ org, locale, permissions }: { org: string; locale: Locale; permissions: string[] }) {
  const text = editorialAdminMessages[locale];
  const base = `/api/cms/organizations/${org}/editorial`;
  const [kind, setKind] = useState<Kind>("news");
  const [language, setLanguage] = useState<Locale>(locale);
  const [items, setItems] = useState<Entry[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [selected, setSelected] = useState<Entry | null>(null);
  const [form, setForm] = useState<Draft>({ ...empty });
  const [creating, setCreating] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const locked = useRef(false);
  const [message, setMessage] = useState("");
  const [stale, setStale] = useState(false);
  const [latest, setLatest] = useState<Entry | null>(null);
  const [creationRecovery, setCreationRecovery] = useState<(CreateAddress & { mustCheck: boolean }) | null>(null);
  const [stored, setStored] = useState<Entry | null>(null);
  const dirty = JSON.stringify(form) !== JSON.stringify(formOf(selected));
  const allowed = (action: string) => permissions.includes(`cms.editorial.${action}`);
  const editable = (creating ? allowed("create") : !!selected && allowed("update") && selected.state === "draft");

  async function api<T>(path: string, method = "GET", data?: unknown): Promise<T> {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (method !== "GET") {
      const csrf = await fetch("/api/session/csrf", { cache: "no-store" });
      if (!csrf.ok) throw new RequestError(csrf.status);
      headers["X-CSRF-Token"] = (await csrf.json()).csrf_token;
    }
    const response = await fetch(path, { method, headers, cache: "no-store", body: data === undefined ? undefined : JSON.stringify(data) });
    if (!response.ok) { const result = await response.json().catch(() => null); throw new RequestError(response.status, result?.error?.code); }
    return response.json() as Promise<T>;
  }
  async function run(work: () => Promise<void>, creationAttempt?: CreateAddress) {
    if (locked.current) return;
    locked.current = true; setBusy(true); setMessage("");
    try { await work(); } catch (error) {
      if (creationAttempt && error instanceof RequestError && error.code === "content_conflict") {
        setCreationRecovery({ ...creationAttempt, mustCheck: false }); setStored(null); setMessage(text.addressConflict);
      } else if (creationAttempt && (!(error instanceof RequestError) || error.status >= 500)) {
        setCreationRecovery({ ...creationAttempt, mustCheck: true }); setStored(null); setMessage(text.createUncertain);
      } else if (error instanceof RequestError && error.status === 409 && selected) { setStale(true); setLatest(null); setMessage(text.conflict); }
      else if (error instanceof RequestError && error.code === "content_conflict") setMessage(text.addressConflict);
      else setMessage(text.error);
    } finally { locked.current = false; setBusy(false); }
  }
  function choose(entry: Entry | null, create = false) {
    setSelected(entry); setForm(formOf(entry)); setCreating(create); setReason(""); setStale(false); setLatest(null); setCreationRecovery(null); setStored(null); setMessage("");
  }
  function saved(entry: Entry) {
    choose(entry); setItems(previous => [entry, ...previous.filter(item => item.id !== entry.id)]); setMessage(text.saved);
  }
  const listPath = (next?: string | null) => `${base}?${new URLSearchParams({ kind, locale: language, limit: "25", ...(next ? { cursor: next } : {}) })}`;
  useEffect(() => {
    let active = true;
    const query = new URLSearchParams({ kind, locale: language, limit: "25" });
    fetch(`${base}?${query}`, { cache: "no-store" }).then(async response => {
      if (!response.ok) throw new Error(); return response.json() as Promise<Batch>;
    }).then(data => { if (active) { setItems(data.items); setCursor(data.next_cursor); } })
      .catch(() => { if (active) setMessage(text.error); });
    return () => { active = false; };
  }, [base, kind, language, text.error]);
  async function load(more = false) {
    const data = await api<Batch>(listPath(more ? cursor : null));
    setItems(previous => more ? [...previous, ...data.items.filter(item => !previous.some(old => old.id === item.id))] : data.items);
    setCursor(data.next_cursor);
  }
  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editable || stale || creationRecovery?.mustCheck) return;
    const start = form.starts_at ? new Date(`${form.starts_at}Z`) : null;
    const end = form.ends_at ? new Date(`${form.ends_at}Z`) : null;
    if ((start && !Number.isFinite(start.getTime())) || (end && !Number.isFinite(end.getTime()))) { setMessage(text.dateError); return; }
    const starts_at = start?.toISOString() ?? null;
    const ends_at = end?.toISOString() ?? null;
    if (starts_at && ends_at && ends_at <= starts_at) { setMessage(text.dateError); return; }
    const values = { title: form.title, body: form.body, starts_at, ends_at, sort_order: form.sort_order };
    await run(async () => saved(selected
      ? await api<Entry>(`${base}/${selected.id}`, "PATCH", { ...values, expected_version: selected.version })
      : await api<Entry>(base, "POST", { ...values, slug: form.slug, kind, locale: language })), selected ? undefined : { kind, locale: language, slug: form.slug });
  }
  async function checkAddress() {
    if (!creationRecovery) return;
    await run(async () => {
      const query = new URLSearchParams({ kind: creationRecovery.kind, locale: creationRecovery.locale, slug: creationRecovery.slug, limit: "1" });
      const result = await api<Batch>(`${base}?${query}`);
      const entry = result.items.find(item => item.kind === creationRecovery.kind && item.locale === creationRecovery.locale && item.slug === creationRecovery.slug) ?? null;
      setStored(entry); setCreationRecovery({ ...creationRecovery, mustCheck: !!entry });
      if (!entry) setMessage(text.notFoundAtAddress);
    });
  }
  async function command(action: "publish" | "archive" | "restore") {
    if (!selected || stale || (dirty && (action === "publish" || selected.state === "draft")) || !allowed(action === "restore" ? "update" : action)) return;
    const localDraft = dirty ? form : null;
    await run(async () => {
      saved(await api<Entry>(`${base}/${selected.id}/${action}`, "POST", { expected_version: selected.version, ...(action === "archive" ? { reason: reason.trim() } : {}) }));
      if (localDraft) setForm(localDraft);
    });
  }
  return <div className="content-admin-grid" aria-busy={busy}>
    <aside aria-label={text.queue}>
      <fieldset disabled={busy || dirty || stale} className="content-admin-filters">
        <label>{text.kind}<select value={kind} onChange={event => { choose(null); setItems([]); setCursor(null); setKind(event.target.value as Kind); }}>{(Object.keys(editorialLabels[locale]) as Kind[]).map(value => <option key={value} value={value}>{editorialLabels[locale][value]}</option>)}</select></label>
        <label>{text.language}<select value={language} onChange={event => { choose(null); setItems([]); setCursor(null); setLanguage(event.target.value as Locale); }}><option value="en">{text.english}</option><option value="ta">{text.tamil}</option></select></label>
        <div className="actions"><button type="button" disabled={!allowed("create")} onClick={() => choose(null, true)}>{text.newEntry}</button><button type="button" onClick={() => run(() => load())}>{text.refresh}</button></div>
      </fieldset>
      {!items.length && <p>{text.empty}</p>}
      <ul className="content-admin-list">{items.map(item => <li key={item.id}><button disabled={busy || dirty || stale} aria-pressed={item.id === selected?.id} onClick={() => run(async () => choose(await api<Entry>(`${base}/${item.id}`)))}>{item.title}<small>{item.slug} · {text[item.state]} · {text.version} {item.version}</small></button></li>)}</ul>
      {cursor && <button disabled={busy || dirty || stale} onClick={() => run(() => load(true))}>{text.more}</button>}
    </aside>
    <section>
      <p role="status">{busy ? text.loading : message}</p>
      {dirty && <p>{text.dirty}</p>}
      {(dirty || stale) && <button disabled={busy} onClick={() => run(async () => choose(selected ? await api<Entry>(`${base}/${selected.id}`) : null, creating))}>{text.discard}</button>}
      {creationRecovery && <div className="content-conflict">
        <button disabled={busy} onClick={checkAddress}>{text.checkAddress}</button>
        {stored && <article><h2>{text.storedEntry} · {text.version} {stored.version}</h2><h3>{stored.title}</h3><p className="content-body">{stored.body}</p><p>{text[stored.state]} · {stored.locale === "en" ? text.english : text.tamil} · {editorialLabels[locale][stored.kind]} · {stored.slug}</p>
          <button disabled={busy} onClick={() => { const local = form; choose(stored); setForm(local); setItems(previous => [stored, ...previous.filter(item => item.id !== stored.id)]); setMessage(text.reviewed); }}>{text.useStored}</button>
          <button disabled={busy} onClick={() => { setCreationRecovery(null); setStored(null); setMessage(text.addressConflict); }}>{text.anotherAddress}</button>
        </article>}
      </div>}
      {stale && selected && <div className="content-conflict">
        <button disabled={busy} onClick={() => run(async () => setLatest(await api<Entry>(`${base}/${selected.id}`)))}>{text.loadLatest}</button>
        {latest && <article><h2>{text.latest} · {text.version} {latest.version}</h2><h3>{latest.title}</h3><p className="content-body">{latest.body}</p><p>{latest.starts_at} {latest.ends_at} · {text.order}: {latest.sort_order}</p>
          <button disabled={busy} onClick={() => { setSelected(latest); setLatest(null); setStale(false); setMessage(text.reviewed); }}>{text.keepChanges}</button></article>}
      </div>}
      {!selected && !creating ? <p>{text.choose}</p> : <>
        {selected && <p>{text[selected.state]} · {text.version} {selected.version} · {selected.locale === "en" ? text.english : text.tamil}</p>}
        {selected?.state === "published" && <p>{text.publishedNote}</p>}
        <form className="account-form content-admin-form" onSubmit={save}>
          <fieldset disabled={busy || !editable || stale || !!creationRecovery?.mustCheck}>
            <label>{text.slug}<input value={form.slug} required pattern="[a-z0-9]+(-[a-z0-9]+)*" maxLength={120} disabled={!!selected} onChange={event => { setForm({ ...form, slug: event.target.value }); setCreationRecovery(null); setStored(null); }} /></label>
            <label>{text.titleField}<input value={form.title} required maxLength={200} onChange={event => setForm({ ...form, title: event.target.value })} /></label>
            <label>{text.body}<textarea value={form.body} required rows={12} maxLength={50000} onChange={event => setForm({ ...form, body: event.target.value })} /></label>
            <label>{text.order}<input type="number" min={0} max={100000} required value={form.sort_order} onChange={event => setForm({ ...form, sort_order: Number(event.target.value) })} /></label>
            <label>{text.starts}<input type="datetime-local" step="1" value={form.starts_at} onChange={event => setForm({ ...form, starts_at: event.target.value })} /></label>
            <label>{text.ends}<input type="datetime-local" step="1" value={form.ends_at} onChange={event => setForm({ ...form, ends_at: event.target.value })} /></label>
            <button type="submit" disabled={!dirty}>{text.save}</button>
          </fieldset>
        </form>
        {selected && <div className="actions">
          {selected.state === "draft" && allowed("publish") && <button disabled={busy || dirty || stale} onClick={() => command("publish")}>{text.publish}</button>}
          {selected.state === "archived" && allowed("update") && <button disabled={busy || stale} onClick={() => command("restore")}>{text.restore}</button>}
          {selected.state !== "archived" && allowed("archive") && <><label>{text.reason}<input value={reason} maxLength={500} disabled={busy || stale || (dirty && selected.state === "draft")} onChange={event => setReason(event.target.value)} /></label><button disabled={busy || stale || (dirty && selected.state === "draft") || !reason.trim()} onClick={() => command("archive")}>{text.archive}</button></>}
          {selected.state === "published" && <Link href={`/${selected.locale}/content/${selected.kind}/${encodeURIComponent(selected.slug)}`}>{text.viewPublic}</Link>}
        </div>}
      </>}
    </section>
  </div>;
}
