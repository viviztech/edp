"use client";
import { useEffect, useRef, useState } from "react";
import { emptyPolicyForm, filePolicyWords, filePurposes, policyFormOf, policyMediaTypes, policyRules,
  type FilePolicy, type FilePolicyCreate, type FilePolicyList, type PolicyForm, type PolicyMime, type PolicyPurpose } from "../../../../lib/file-policy-content";

class RequestError extends Error { constructor(public status: number, public code = "request_failed") { super(code); } }
export default function FilePolicyWorkspace({ org, locale, permissions }: { org: string; locale: "en" | "ta"; permissions: string[] }) {
  const t = filePolicyWords[locale], base = `/api/file-policies/organizations/${org}/policies`;
  const canManage = permissions.includes("files.policy.manage");
  const [filter, setFilter] = useState<PolicyPurpose | "">("");
  const [items, setItems] = useState<FilePolicy[]>([]), [cursor, setCursor] = useState<string | null>(null);
  const [selected, setSelected] = useState<FilePolicy | null>(null), [creating, setCreating] = useState(false);
  const [copyFrom, setCopyFrom] = useState<string | null>(null), [form, setForm] = useState<PolicyForm>(emptyPolicyForm);
  const [reason, setReason] = useState(""), [busy, setBusy] = useState(true), [message, setMessage] = useState("");
  const [stale, setStale] = useState(false), [latest, setLatest] = useState<FilePolicy | null>(null);
  const [pendingCreate, setPendingCreate] = useState<FilePolicyCreate | null>(null);
  const locked = useRef(true);
  const dirty = JSON.stringify(form) !== JSON.stringify(policyFormOf(selected));
  const listUrl = `${base}?${new URLSearchParams({ limit: "25", ...(filter ? { purpose: filter } : {}) })}`;
  async function api<T>(path: string, method = "GET", data?: unknown): Promise<T> {
    const headers: Record<string, string> = {};
    if (method !== "GET") {
      const csrf = await fetch("/api/session/csrf", { cache: "no-store" }); if (!csrf.ok) throw new RequestError(csrf.status);
      headers["x-csrf-token"] = (await csrf.json()).csrf_token; headers["Content-Type"] = "application/json";
    }
    const response = await fetch(path, { method, headers, cache: "no-store", ...(data ? { body: JSON.stringify(data) } : {}) });
    if (!response.ok) { const value = await response.json().catch(() => null); throw new RequestError(response.status, value?.error?.code); }
    return response.json() as Promise<T>;
  }
  useEffect(() => {
    let active = true;
    fetch(listUrl, { cache: "no-store" }).then(async response => { if (!response.ok) throw new Error(); return response.json() as Promise<FilePolicyList>; })
      .then(data => { if (active) { setItems(data.items); setCursor(data.next_cursor); } })
      .catch(() => { if (active) setMessage(t.error); }).finally(() => { if (active) { locked.current = false; setBusy(false); } });
    return () => { active = false; };
  }, [listUrl, t.error]);
  async function run(work: () => Promise<void>) {
    if (locked.current) return;
    locked.current = true; setBusy(true); setMessage("");
    try { await work(); } catch { setMessage(t.error); }
    finally { locked.current = false; setBusy(false); }
  }
  function choose(value: FilePolicy | null, create = false) {
    setSelected(value); setCreating(create); setCopyFrom(null); setForm(policyFormOf(value)); setReason(""); setStale(false); setLatest(null); setPendingCreate(null); setMessage("");
  }
  async function load(more = false) {
    const data = await api<FilePolicyList>(listUrl + (more && cursor ? `&cursor=${cursor}` : ""));
    setItems(previous => more ? [...previous, ...data.items.filter(value => !previous.some(item => item.id === value.id))] : data.items); setCursor(data.next_cursor);
  }
  function sync(value: FilePolicy) {
    setItems(previous => [value, ...previous.filter(item => item.id !== value.id)].filter(item => !filter || item.purpose === filter));
  }
  async function saved(value: FilePolicy) {
    choose(value); sync(value); setMessage(t.saved);
    try { await load(); } catch { setItems(!filter || value.purpose === filter ? [value] : []); setCursor(null); setMessage(t.savedRefresh); }
  }
  async function create(body: FilePolicyCreate) {
    setPendingCreate(body);
    try { await saved(await api<FilePolicy>(base, "POST", body)); }
    catch (error) {
      if (error instanceof RequestError && error.status < 500) { setPendingCreate(null); setMessage(error.status === 403 ? t.denied : error.code === "file_policy_draft_exists" ? t.draftExists : t.invalid); }
      else setMessage(t.uncertainCreate);
    }
  }
  async function update(method: "PATCH" | "POST", path: string, data: unknown) {
    setStale(true); setLatest(null);
    try { await saved(await api<FilePolicy>(path, method, data)); }
    catch (error) {
      if (error instanceof RequestError && error.status === 422) { setStale(false); setMessage(t.invalid); }
      else setMessage(error instanceof RequestError && error.status === 409 ? t.conflict : t.uncertain);
    }
  }
  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!canManage || stale || pendingCreate || (!creating && selected?.state !== "draft")) return;
    const rules = policyRules(form);
    if (!rules || !reason.trim()) { setMessage(t.invalid); return; }
    if (creating) {
      const body: FilePolicyCreate = { ...rules, purpose: form.purpose as PolicyPurpose, client_request_id: crypto.randomUUID(), reason: reason.trim(), ...(copyFrom ? { copy_from: copyFrom } : {}) };
      await run(() => create(body));
    } else if (selected) await run(() => update("PATCH", `${base}/${selected.id}`, { ...rules, expected_version: selected.version, reason: reason.trim() }));
  }
  async function command(action: "publish" | "retire") {
    if (!selected || !canManage || stale || pendingCreate || dirty || !reason.trim()) return;
    await run(() => update("POST", `${base}/${selected.id}/${action}`, { expected_version: selected.version, reason: reason.trim() }));
  }
  function copy() {
    if (!selected || !canManage || stale || busy || pendingCreate) return;
    setCopyFrom(selected.id); setSelected(null); setCreating(true); setReason(""); setMessage(t.copied);
  }
  const blocked = busy || stale || !!pendingCreate;
  const editable = canManage && (creating || selected?.state === "draft");
  return <div className="file-policy-grid" aria-busy={busy}>
    <aside aria-label={t.queue}><fieldset disabled={blocked || dirty}>
      <label>{t.filterPurpose}<select value={filter} onChange={event => { locked.current = true; setBusy(true); choose(null); setItems([]); setCursor(null); setFilter(event.target.value as PolicyPurpose | ""); }}><option value="">{t.all}</option>{filePurposes.map(value => <option key={value} value={value}>{t.purposes[value]}</option>)}</select></label>
      <div className="actions"><button type="button" disabled={!canManage} onClick={() => choose(null, true)}>{t.new}</button><button type="button" onClick={() => run(() => load())}>{t.refresh}</button></div>
    </fieldset>
      {!busy && !items.length && <p>{t.empty}</p>}
      <ul>{items.map(value => <li key={value.id}><button disabled={blocked || dirty} aria-pressed={value.id === selected?.id} onClick={() => run(async () => choose(await api<FilePolicy>(`${base}/${value.id}`)))}>{value.name}<small>{t.purposes[value.purpose]} · {t.edition} {value.edition} · {t[value.state]} · v{value.version}</small></button></li>)}</ul>
      {cursor && <button disabled={blocked || dirty} onClick={() => run(() => load(true))}>{t.more}</button>}
    </aside>
    <section aria-label={t.details}><p role="status" aria-live="polite">{busy ? t.loading : message}</p>
      {pendingCreate && <button disabled={busy} onClick={() => run(() => create(pendingCreate))}>{t.retryCreate}</button>}
      {dirty && <p>{t.dirty}</p>}
      {(dirty || stale) && !pendingCreate && <button disabled={busy} onClick={() => run(async () => choose(selected ? await api<FilePolicy>(`${base}/${selected.id}`) : null, creating))}>{t.discard}</button>}
      {stale && selected && <div className="file-policy-conflict"><button disabled={busy} onClick={() => run(async () => { const value = await api<FilePolicy>(`${base}/${selected.id}`); setLatest(value); sync(value); })}>{t.loadLatest}</button>
        {latest && <article><h2>{t.current}</h2><p>{latest.name} · {t[latest.state]} · {t.edition} {latest.edition} · v{latest.version}</p>
          <dl><dt>{t.formats}</dt><dd>{latest.allowed_mime_types.join(", ")}</dd><dt>{t.max_file_bytes}</dt><dd>{latest.max_file_bytes}</dd><dt>{t.max_files}</dt><dd>{latest.max_files}</dd><dt>{t.retention_days}</dt><dd>{latest.retention_days}</dd><dt>{t.rejected_retention_days}</dt><dd>{latest.rejected_retention_days}</dd><dt>{t.frozen}</dt><dd>{latest.allow_frozen_disposal ? t.yes : t.no}</dd></dl>
          <h3>{t.notice_en}</h3><p>{latest.notice_en}</p><h3>{t.notice_ta}</h3><p>{latest.notice_ta}</p>
          <button disabled={busy} onClick={() => { setSelected(latest); setLatest(null); setStale(false); setMessage(t.reviewed); }}>{t.useLatest}</button></article>}
      </div>}
      {!selected && !creating ? <p>{t.pick}</p> : <>
        {selected && <p>{t.edition} {selected.edition} · {t.version} {selected.version} · {t[selected.state]}</p>}
        {selected?.state !== "draft" && selected && <p>{t.immutable}</p>}
        {copyFrom && <p>{t.copiedFrom}: <span className="file-policy-reference">{copyFrom}</span></p>}
        <form className="account-form file-policy-form" aria-label={t.details} onSubmit={save}>
          <fieldset disabled={blocked || !editable}>
            <label>{t.purpose}<select required value={form.purpose} disabled={!!selected || !!copyFrom} onChange={event => setForm({ ...form, purpose: event.target.value as PolicyPurpose | "" })}><option value="">{t.choose}</option>{filePurposes.map(value => <option key={value} value={value}>{t.purposes[value]}</option>)}</select></label>
            <label>{t.name}<input required maxLength={160} value={form.name} onChange={event => setForm({ ...form, name: event.target.value })} /></label>
            {(["notice_en", "notice_ta"] as const).map(key => <label key={key}>{t[key]}<textarea required rows={5} maxLength={4000} lang={key === "notice_en" ? "en" : "ta"} value={form[key]} onChange={event => setForm({ ...form, [key]: event.target.value })} /></label>)}
            <fieldset><legend>{t.formats}</legend>{policyMediaTypes.map(value => <label className="file-policy-check" key={value}><input type="checkbox" checked={form.allowed_mime_types.includes(value)} onChange={event => setForm({ ...form, allowed_mime_types: event.target.checked ? [...form.allowed_mime_types, value].sort() : form.allowed_mime_types.filter(item => item !== value) as PolicyMime[] })} />{value}</label>)}</fieldset>
            {(["max_file_bytes", "max_files", "retention_days", "rejected_retention_days"] as const).map(key => <label key={key}>{t[key]}<input type="number" required min={1} max={key === "max_file_bytes" ? 104857600 : key === "max_files" ? 100 : 3650} step={1} value={form[key]} onChange={event => setForm({ ...form, [key]: event.target.value })} /></label>)}
            <label>{t.frozen}<select required value={form.allow_frozen_disposal} onChange={event => setForm({ ...form, allow_frozen_disposal: event.target.value as PolicyForm["allow_frozen_disposal"] })}><option value="">{t.choose}</option><option value="false">{t.blockFrozen}</option><option value="true">{t.allowFrozen}</option></select></label><p>{t.frozenNote}</p>
          </fieldset>
          <label>{t.reason}<textarea rows={2} required maxLength={500} disabled={blocked || !canManage} value={reason} onChange={event => setReason(event.target.value)} /></label>
          {editable && <button type="submit" disabled={blocked || !dirty || !reason.trim()}>{t.save}</button>}
        </form>
        <div className="actions">
          {selected?.state === "draft" && canManage && <button disabled={blocked || dirty || !reason.trim()} onClick={() => command("publish")}>{t.publish}</button>}
          {selected && selected.state !== "retired" && canManage && <button disabled={blocked || dirty || !reason.trim()} onClick={() => command("retire")}>{t.retire}</button>}
          {selected && selected.state !== "draft" && canManage && <button disabled={blocked} onClick={copy}>{t.copy}</button>}
        </div><p>{t.publicationNote}</p>
      </>}
    </section>
  </div>;
}
