"use client";
import { useState } from "react";
import { toolsCopy, type ToolsLocale } from "../../../lib/business-tools-copy";
import { CommandState, type Contact, type ContactFields, localInput, type Page, Pager, read, type Task, type TaskFields, useCommand, useDirtyGuard } from "./client";
import { SavedReview } from "./card";
const contactEmpty: ContactFields = { name: "", email: "", phone: "", notes: "", status: "lead" };
function contactFields(c: ContactFields): ContactFields { return { name: c.name, email: c.email, phone: c.phone, notes: c.notes, status: c.status }; }
const taskEmpty: TaskFields = { title: "", notes: "", due_at: "", status: "pending" };
function taskFields(c: TaskFields): TaskFields { return { title: c.title, notes: c.notes, due_at: c.due_at, status: c.status }; }

export function Contacts({ base, locale, initial, onContacts }: { base: string; locale: ToolsLocale; initial: Page<Contact>; onContacts: (items: Contact[]) => void }) {
  const t = toolsCopy[locale]; const command = useCommand(t);
  const [data, setData] = useState(initial); const [editing, setEditing] = useState<Contact | null>(null);
  const [draft, setDraft] = useState<ContactFields>(contactEmpty); const [loaded, setLoaded] = useState(false); const [error, setError] = useState("");
  const [latest, setLatest] = useState<Contact | null>(null);
  const [filterStatus, setFilterStatus] = useState(""); const [search, setSearch] = useState("");
  const dirty = JSON.stringify(draft) !== JSON.stringify(contactFields(editing ?? contactEmpty));
  useDirtyGuard(dirty || command.pending);
  function select(contact: Contact | null) { setEditing(contact); setDraft(contactFields(contact ?? contactEmpty)); setLoaded(false); setLatest(null); }
  async function load(offset = data.offset) {
    try { const query = new URLSearchParams({ limit: "25", offset: String(offset) });
      if (filterStatus) query.set("status", filterStatus); if (search.trim()) query.set("search", search.trim());
      const body = await read<Page<Contact>>(`${base}/contacts?${query}`);
      setLatest(editing ? await read<Contact>(`${base}/contacts/${editing.id}`) : null);
      setData(body); onContacts(body.items); setLoaded(true); setError(""); }
    catch { setError(t.unavailable); }
  }
  return <section className="program-panel"><h2>{t.contacts}</h2><CommandState command={command} t={t} /><p role="status">{error}</p>
    <form onSubmit={event => { event.preventDefault(); void load(0); }}><fieldset disabled={command.blocked || dirty}><div className="tools-fields">
      <label>{t.search}<input maxLength={160} value={search} onChange={event => setSearch(event.target.value)} /></label>
      <label>{t.filterStatus}<select value={filterStatus} onChange={event => setFilterStatus(event.target.value)}><option value="">{t.all}</option><option value="lead">{t.lead}</option><option value="customer">{t.customerState}</option><option value="archived">{t.archived}</option></select></label>
    </div><button type="submit">{t.applyFilters}</button></fieldset></form>
    <ul className="program-list">{data.items.map(c => <li key={c.id}><strong>{c.name}</strong> · {c.status === "customer" ? t.customerState : t[c.status]}
      <button type="button" disabled={command.blocked || dirty} onClick={() => select(c)}>{t.edit}</button></li>)}</ul>
    {!data.items.length && <p>{t.noItems}</p>}<Pager offset={data.offset} count={data.items.length} busy={command.blocked || dirty} onChange={offset => void load(offset)} t={t} />
    <button type="button" disabled={command.blocked || dirty} onClick={() => select(null)}>{t.newContact}</button>
    <form onSubmit={e => { e.preventDefault(); command.run<Contact>(editing ? `${base}/contacts/${editing.id}/update` : `${base}/contacts`, { ...draft, ...(editing ? { expected_version: editing.version } : {}) }, c => { select(c); void load(); }); }}>
      <fieldset disabled={command.busy || command.pending || editing?.status === "archived"}><div className="tools-fields">
        <label>{t.contactName}<input required maxLength={160} value={draft.name} onChange={e => setDraft(old => ({ ...old, name: e.target.value }))} /></label>
        <label>{t.contactEmail}<input type="email" maxLength={254} value={draft.email} onChange={e => setDraft(old => ({ ...old, email: e.target.value }))} /></label>
        <label>{t.contactPhone}<input maxLength={40} value={draft.phone} onChange={e => setDraft(old => ({ ...old, phone: e.target.value }))} /></label>
        <label>{t.status}<select value={draft.status} onChange={e => setDraft(old => ({ ...old, status: e.target.value as ContactFields["status"] }))}><option value="lead">{t.lead}</option><option value="customer">{t.customerState}</option><option value="archived">{t.archived}</option></select></label>
        <label>{t.notes}<textarea maxLength={2000} value={draft.notes} onChange={e => setDraft(old => ({ ...old, notes: e.target.value }))} /></label>
      </div><button type="submit" disabled={command.blocked}>{t.save}</button></fieldset></form>
    <button type="button" disabled={command.busy || command.pending || (command.stale && !loaded)} onClick={() => { select(latest ?? editing); command.reconcile(); }}>{editing ? t.useSaved : t.discard}</button>
    <SavedReview command={command} loaded={loaded} onLoad={() => void load()} onReconcile={() => { if (latest) setEditing(latest); setLoaded(false); }} t={t}>
      {(latest ? [latest] : data.items).map(c => <p key={c.id}>{c.name} · v{c.version} · {c.email} {c.phone} · {c.notes} · {c.status === "customer" ? t.customerState : t[c.status]}</p>)}
    </SavedReview>
  </section>;
}

export function Tasks({ base, locale, initial, contacts }: { base: string; locale: ToolsLocale; initial: Page<Task>; contacts: Contact[] }) {
  const t = toolsCopy[locale]; const command = useCommand(t);
  const [data, setData] = useState(initial); const [editing, setEditing] = useState<Task | null>(null);
  const [draft, setDraft] = useState<TaskFields>(taskEmpty); const [contact, setContact] = useState(""); const [filter, setFilter] = useState("");
  const [filterContact, setFilterContact] = useState("");
  const [loaded, setLoaded] = useState(false); const [error, setError] = useState("");
  const [latest, setLatest] = useState<Task | null>(null);
  const dirty = JSON.stringify(draft) !== JSON.stringify(taskFields(editing ?? taskEmpty)) || (!editing && !!contact);
  useDirtyGuard(dirty || command.pending);
  function select(task: Task | null) { setEditing(task); setDraft(taskFields(task ?? taskEmpty)); setContact(task?.contact_id ?? ""); setLoaded(false); setLatest(null); }
  async function load(offset = data.offset, status = filter, contactId = filterContact) {
    try { const query = new URLSearchParams({ limit: "25", offset: String(offset) });
      if (status) query.set("status", status); if (contactId) query.set("contact_id", contactId);
      const body = await read<Page<Task>>(`${base}/tasks?${query}`);
      setLatest(editing ? await read<Task>(`${base}/tasks/${editing.id}`) : null);
      setData(body); setLoaded(true); setFilter(status); setFilterContact(contactId); setError(""); }
    catch { setError(t.unavailable); }
  }
  const date = (iso: string) => new Intl.DateTimeFormat(locale === "ta" ? "ta-IN" : "en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(iso));
  return <section className="program-panel"><h2>{t.tasks}</h2><p>{t.taskNote}</p><CommandState command={command} t={t} /><p role="status">{error}</p>
    <div className="tools-fields"><label>{t.filterStatus}<select value={filter} disabled={command.blocked || dirty} onChange={e => void load(0, e.target.value)}><option value="">{t.all}</option>{(["pending", "completed", "cancelled"] as const).map(s => <option key={s} value={s}>{t[s]}</option>)}</select></label>
      <label>{t.filterContact}<select value={filterContact} disabled={command.blocked || dirty} onChange={e => void load(0, filter, e.target.value)}><option value="">{t.all}</option>{contacts.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}{filterContact && !contacts.some(c => c.id === filterContact) && <option value={filterContact}>{t.contactName}</option>}</select></label></div>
    <ul className="program-list">{data.items.map(task => <li key={task.id}><strong>{task.title}</strong> {t[task.status]} · <time dateTime={task.due_at}>{date(task.due_at)}</time>
      <button type="button" disabled={command.blocked || dirty} onClick={() => select(task)}>{t.edit}</button></li>)}</ul>
    {!data.items.length && <p>{t.noItems}</p>}<Pager offset={data.offset} count={data.items.length} busy={command.blocked || dirty} onChange={offset => void load(offset)} t={t} />
    <button type="button" disabled={command.blocked || dirty} onClick={() => select(null)}>{t.newTask}</button>
    <form onSubmit={e => { e.preventDefault(); command.run<Task>(editing ? `${base}/tasks/${editing.id}/update` : `${base}/tasks`, editing ? { ...draft, expected_version: editing.version } : { title: draft.title, notes: draft.notes, due_at: draft.due_at, contact_id: contact }, task => { select(task); void load(); }); }}>
      <fieldset disabled={command.busy || command.pending || (!!editing && editing.status !== "pending")}><div className="tools-fields">
        <label>{t.contactName}<select required value={contact} disabled={!!editing} onChange={e => setContact(e.target.value)}><option value="">{t.contacts}</option>{contacts.filter(c => c.status !== "archived" || c.id === contact).map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          {contact && !contacts.some(c => c.id === contact) && <option value={contact}>{t.contactName}</option>}</select></label>
        <label>{t.titleField}<input required maxLength={160} value={draft.title} onChange={e => setDraft(old => ({ ...old, title: e.target.value }))} /></label>
        <label>{t.due}<input required type="datetime-local" value={localInput(draft.due_at)} onChange={e => { const date = new Date(e.target.value); setDraft(old => ({ ...old, due_at: Number.isFinite(date.getTime()) ? date.toISOString() : "" })); }} /></label>
        {editing && <label>{t.status}<select value={draft.status} onChange={e => setDraft(old => ({ ...old, status: e.target.value as TaskFields["status"] }))}>{(["pending", "completed", "cancelled"] as const).map(s => <option key={s} value={s}>{t[s]}</option>)}</select></label>}
        <label>{t.notes}<textarea maxLength={2000} value={draft.notes} onChange={e => setDraft(old => ({ ...old, notes: e.target.value }))} /></label>
      </div><button type="submit" disabled={command.blocked}>{t.save}</button></fieldset></form>
    <button type="button" disabled={command.busy || command.pending || (command.stale && !loaded)} onClick={() => { select(latest ?? editing); command.reconcile(); }}>{editing ? t.useSaved : t.discard}</button>
    <SavedReview command={command} loaded={loaded} onLoad={() => void load()} onReconcile={() => { if (latest) setEditing(latest); setLoaded(false); }} t={t}>
      {(latest ? [latest] : data.items).map(task => <p key={task.id}>{task.title} · v{task.version} · {t[task.status]} · {date(task.due_at)} · {task.notes}</p>)}
    </SavedReview>
  </section>;
}
