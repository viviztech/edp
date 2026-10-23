"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import type { components } from "../../../lib/api-contracts";
import { categories, label, priorities, statuses, textAttachments, words, type AttachmentInput, type Locale, type Ticket } from "./content";

type TicketList = components["schemas"]["TicketList"];
type MessageList = components["schemas"]["MessageList"];
type HistoryList = components["schemas"]["HistoryList"];
type AssigneeList = components["schemas"]["AssigneeList"];
type NoticeList = components["schemas"]["NoticeList"];
type Preference = components["schemas"]["HelpdeskPreferenceView"];
type Create = components["schemas"]["TicketCreate"];

export async function helpdeskMutation(url: string, body: object) {
  const response = await fetch("/api/session/csrf", { cache: "no-store" });
  if (!response.ok) throw new Error("csrf");
  const { csrf_token } = await response.json() as { csrf_token: string };
  return fetch(url, { method: "POST", headers: { "Content-Type": "application/json", "x-csrf-token": csrf_token }, body: JSON.stringify(body) });
}
async function get<T>(url: string): Promise<T> {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(response.status === 403 ? "access" : "load");
  return response.json() as Promise<T>;
}

function Files({ locale, disabled, files, change, clearKey, onReading }: { locale: Locale; disabled: boolean; files: AttachmentInput[];
  change: (files: AttachmentInput[], error?: string) => void; clearKey: number; onReading: (reading: boolean) => void }) {
  const t = words[locale]; const [reading, setReading] = useState(false);
  return <div><label>{t.attachments}<input key={clearKey} type="file" accept=".txt,text/plain" multiple disabled={disabled || reading}
    onChange={(event) => { setReading(true); onReading(true); void textAttachments(event.target.files).then((data) => change(data)).catch(() => change([], t.attachmentError)).finally(() => { setReading(false); onReading(false); }); }} /></label>
    <p className="helpdesk-hint">{t.attachmentHint}</p>{files.length > 0 && <p>{t.selected}: {files.map((file) => file.filename).join(", ")}</p>}</div>;
}

function Notices({ base, locale, open }: { base: string; locale: Locale; open: (id: string) => void }) {
  const t = words[locale]; const [batch, setBatch] = useState<NoticeList | null>(null); const [preference, setPreference] = useState<Preference | null>(null);
  const [enabled, setEnabled] = useState(true); const [busy, setBusy] = useState(false); const [paused, setPaused] = useState(false);
  const [message, setMessage] = useState(""); const lock = useRef(false); const settingDirty = useRef(false);
  const load = useCallback(async () => {
    if (lock.current) return; lock.current = true; setBusy(true);
    try { const [notices, setting] = await Promise.all([get<NoticeList>(`${base}/notices?limit=25`), get<Preference>(`${base}/preference`)]);
      setBatch(notices); setPreference(setting); if (!settingDirty.current) setEnabled(setting.enabled); setPaused(false); setMessage("");
    } catch { setMessage(t.error); } finally { lock.current = false; setBusy(false); }
  }, [base, t.error]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  async function write(path: string, body: object, preferenceWrite = false) {
    if (lock.current || paused) return; lock.current = true; setBusy(true); setMessage("");
    try { const response = await helpdeskMutation(`${base}/${path}`, body); if (!response.ok) throw new Error();
      if (preferenceWrite) { const setting = await response.json() as Preference; setPreference(setting); setEnabled(setting.enabled); settingDirty.current = false; }
      else { const notice = await response.json() as NoticeList["items"][number]; setBatch((old) => old && ({ ...old, items: old.items.map((item) => item.id === notice.id ? notice : item) })); }
      setMessage(t.done);
    } catch { setPaused(true); setMessage(t.preferenceConflict); } finally { lock.current = false; setBusy(false); }
  }
  return <section className="helpdesk-panel" aria-label={t.notices}><h2>{t.notices}</h2><p>{t.optOut}</p>
    <p role="status">{message}</p><button disabled={busy} onClick={() => { void load(); }}>{t.refreshNotices}</button>
    {preference && <form onSubmit={(event) => { event.preventDefault(); void write("preference", { expected_version: preference.version, enabled }, true); }}>
      <label className="helpdesk-check"><input type="checkbox" checked={enabled} disabled={busy || paused} onChange={(event) => { settingDirty.current = true; setEnabled(event.target.checked); }} />{t.noticePreference}</label>
      <button disabled={busy || paused}>{t.savePreference}</button></form>}
    {batch && !batch.items.length && <p>{t.noNotices}</p>}
    <ul>{batch?.items.map((notice) => <li key={notice.id}><p>{label(notice.event, locale)} · {new Date(notice.created_at).toLocaleString(locale)} · {t.version} {notice.ticket_version}</p>
      <button disabled={busy} onClick={() => open(notice.ticket_id)}>{t.openNotice}</button>{notice.read_at ? <span>{t.alreadyRead}</span> : <button disabled={busy || paused}
        onClick={() => { void write(`notices/${notice.id}/read`, { expected_version: notice.version }); }}>{t.read}</button>}</li>)}</ul>
    {batch?.next_cursor && <button disabled={busy} onClick={async () => { setBusy(true); try { const more = await get<NoticeList>(`${base}/notices?limit=25&cursor=${batch.next_cursor}`);
      setBatch((old) => old && ({ items: [...old.items, ...more.items.filter((item) => !old.items.some((previous) => previous.id === item.id))], next_cursor: more.next_cursor }));
    } catch { setMessage(t.error); } finally { setBusy(false); } }}>{t.more}</button>}
  </section>;
}

export default function HelpdeskWorkspace({ org, locale, staff = false, userId, permissions = [] }: {
  org: string; locale: Locale; staff?: boolean; userId: string; permissions?: string[];
}) {
  const t = words[locale]; const base = `/api/helpdesk/organizations/${org}`;
  const admin = permissions.includes("ticket.admin"); const canAssign = permissions.includes("ticket.assign"); const canUpdate = permissions.includes("ticket.update");
  const [batch, setBatch] = useState<TicketList | null>(null); const [query, setQuery] = useState(staff ? "queue=assigned&limit=25" : "queue=mine&limit=25");
  const [ticket, setTicket] = useState<Ticket | null>(null); const [messages, setMessages] = useState<MessageList | null>(null); const [history, setHistory] = useState<HistoryList | null>(null);
  const [assignees, setAssignees] = useState<AssigneeList | null>(null); const [loading, setLoading] = useState(true); const [busy, setBusy] = useState(false); const [paused, setPaused] = useState(false);
  const [message, setMessage] = useState(""); const lock = useRef(false); const generation = useRef(0); const listGeneration = useRef(0);
  const [reply, setReply] = useState(""); const [internal, setInternal] = useState(false); const [replyFiles, setReplyFiles] = useState<AttachmentInput[]>([]); const [replyFileKey, setReplyFileKey] = useState(0);
  const [assignmentReason, setAssignmentReason] = useState(""); const [assignee, setAssignee] = useState(userId); const [statusReason, setStatusReason] = useState(""); const [nextStatus, setNextStatus] = useState("in_progress");
  const [priorityReason, setPriorityReason] = useState(""); const [nextPriority, setNextPriority] = useState("normal"); const [reopenReason, setReopenReason] = useState("");
  const [createFiles, setCreateFiles] = useState<AttachmentInput[]>([]); const [createFileKey, setCreateFileKey] = useState(0); const [createError, setCreateError] = useState(""); const [replyError, setReplyError] = useState("");
  const [createPending, setCreatePending] = useState<Create | null>(null); const createForm = useRef<HTMLFormElement>(null);
  const [createFileError, setCreateFileError] = useState(false); const [readingCreate, setReadingCreate] = useState(false); const [readingReply, setReadingReply] = useState(false); const [createDirty, setCreateDirty] = useState(false);
  const [claimReason, setClaimReason] = useState(""); const [claimPaused, setClaimPaused] = useState(false);
  const ticketDirty = Boolean(reply || replyFiles.length || assignmentReason || statusReason || priorityReason || reopenReason);
  const dirty = ticketDirty || Boolean(claimReason);
  useEffect(() => { const guard = (event: BeforeUnloadEvent) => { if (dirty || createPending || createDirty || busy || readingCreate || readingReply) { event.preventDefault(); event.returnValue = ""; } };
    window.addEventListener("beforeunload", guard); return () => window.removeEventListener("beforeunload", guard); }, [dirty, createPending, createDirty, busy, readingCreate, readingReply]);

  const loadList = useCallback(async (search: string, append = false) => {
    const current = ++listGeneration.current;
    try { const data = await get<TicketList>(`${base}/tickets?${search}`); if (current !== listGeneration.current) return; setBatch((old) => append && old ? {
      items: [...old.items, ...data.items.filter((item) => !old.items.some((previous) => previous.id === item.id))], next_cursor: data.next_cursor } : data); setClaimPaused(false);
    } catch (error: unknown) { if (current === listGeneration.current) setMessage(error instanceof Error && error.message === "access" ? t.access : t.error); } finally { if (current === listGeneration.current) setLoading(false); }
  }, [base, t.access, t.error]);
  useEffect(() => { void Promise.resolve().then(() => loadList(staff ? "queue=assigned&limit=25" : "queue=mine&limit=25"));
    if (staff && canAssign) { void get<AssigneeList>(`${base}/assignees?limit=25`).then(setAssignees).catch(() => setMessage(t.error)); }
    return () => { generation.current += 1; listGeneration.current += 1; };
  }, [base, canAssign, loadList, staff, t.error]);

  async function loadTicket(id: string, preserve = false) {
    if (lock.current || readingReply) return;
    if (!preserve && dirty && !window.confirm(t.discard)) return;
    const current = ++generation.current; setBusy(true); setMessage("");
    try { const [detail, conversation, events] = await Promise.all([get<Ticket>(`${base}/tickets/${id}`), get<MessageList>(`${base}/tickets/${id}/messages?limit=25`), get<HistoryList>(`${base}/tickets/${id}/history?limit=25`)]);
      if (generation.current !== current) return;
      setTicket(detail); setMessages(conversation); setHistory(events); setPaused(false);
      setBatch((old) => old && ({ ...old, items: old.items.map((item) => item.id === id ? detail : item) }));
      if (!preserve) clearTicketDrafts();
      else setMessage(t.refreshed);
    } catch (error: unknown) { if (generation.current === current) { setPaused(true); setMessage(error instanceof Error && error.message === "access" ? t.access : t.error); } }
    finally { if (generation.current === current) setBusy(false); }
  }
  function clearTicketDrafts() {
    setReply(""); setInternal(false); setReplyFiles([]); setReplyFileKey((old) => old + 1); setAssignmentReason(""); setStatusReason(""); setPriorityReason(""); setReopenReason(""); setReplyError(""); setClaimReason("");
  }
  async function write(path: string, body: object, clear: () => void) {
    if (!ticket || lock.current || paused) return; lock.current = true; setBusy(true); setMessage("");
    let committed = false;
    try { const response = await helpdeskMutation(`${base}/tickets/${ticket.id}/${path}`, { expected_version: ticket.version, ...body });
      if (!response.ok) { setPaused(true); setMessage(response.status === 403 ? t.access : t.conflict); return; }
      const latest = await response.json() as Ticket; committed = true; setTicket(latest); clear();
      setBatch((old) => old && ({ ...old, items: old.items.map((item) => item.id === latest.id ? latest : item) }));
      const [conversation, events] = await Promise.all([get<MessageList>(`${base}/tickets/${latest.id}/messages?limit=25`), get<HistoryList>(`${base}/tickets/${latest.id}/history?limit=25`)]);
      setMessages(conversation); setHistory(events); setMessage(t.done);
    } catch { setPaused(true); setMessage(committed ? `${t.done} ${t.refresh}` : t.conflict); } finally { lock.current = false; setBusy(false); }
  }
  async function create(body: Create) {
    if (lock.current) return; lock.current = true; setBusy(true); setMessage(""); setCreatePending(body);
    try { const response = await helpdeskMutation(`${base}/tickets`, body); if (!response.ok) {
      if ([400, 403, 422].includes(response.status)) { setCreatePending(null); setCreateError(response.status === 403 ? t.access : t.error); } else setCreateError(t.creationRecovery); return;
    }
      const created = await response.json() as Ticket; setCreatePending(null); setCreateError(""); setCreateDirty(false); createForm.current?.reset(); setCreateFiles([]); setCreateFileKey((old) => old + 1);
      setBatch((old) => ({ items: [created, ...(old?.items.filter((item) => item.id !== created.id) ?? [])], next_cursor: old?.next_cursor ?? null })); setMessage(t.requestRecorded);
      lock.current = false; await loadTicket(created.id);
    } catch { setCreateError(t.creationRecovery); } finally { lock.current = false; setBusy(false); }
  }
  function submitCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (createPending) return; const form = new FormData(event.currentTarget);
    const category = String(form.get("category")); const priority = String(form.get("priority"));
    if (!categories.includes(category as typeof categories[number]) || !["low", "normal", "high"].includes(priority)) return;
    void create({ request_id: crypto.randomUUID(), category: category as Create["category"], subject: String(form.get("subject")), body: String(form.get("body")), priority: priority as Create["priority"], attachments: createFiles });
  }
  async function claim(item: TicketList["items"][number]) {
    if (lock.current || claimPaused || readingReply || claimReason.trim().length < 3) return;
    if (ticket && ticket.id !== item.id && ticketDirty && !window.confirm(t.discard)) return;
    lock.current = true; setBusy(true); setMessage("");
    try { const response = await helpdeskMutation(`${base}/tickets/${item.id}/assignment`, { expected_version: item.version, assignee_user_id: userId, reason: claimReason });
      if (!response.ok) throw new Error(); const latest = await response.json() as Ticket;
      setBatch((old) => old && ({ ...old, items: old.items.map((entry) => entry.id === item.id ? latest : entry) }));
      clearTicketDrafts(); lock.current = false; await loadTicket(item.id, true);
    } catch { setClaimPaused(true); setMessage(t.conflict); } finally { lock.current = false; setBusy(false); }
  }
  const allowedStatuses = !ticket ? [] : ticket.status === "assigned" ? ["in_progress"] : ticket.status === "in_progress" ? ["waiting_for_user", "resolved"] : ticket.status === "waiting_for_user" ? ["in_progress", "resolved"] : ticket.status === "resolved" ? ["closed"] : [];
  const writable = ticket?.access === "owner" || admin || (ticket?.access === "staff" && ticket.assignee_user_id === userId && canUpdate);
  const staffAccess = staff && ticket?.access === "staff";
  const disabled = busy || paused || readingCreate || readingReply; const choiceStatus = allowedStatuses.includes(nextStatus) ? nextStatus : allowedStatuses[0];

  return <div className="helpdesk-workspace"><h1>{staff ? t.staff : t.title}</h1><p role="status" aria-live="polite">{message}</p>
    {!staff && <section className="helpdesk-panel" aria-label={t.create}><h2>{t.create}</h2><p role="alert">{createError}</p>
      <form ref={createForm} onChange={() => setCreateDirty(true)} onSubmit={submitCreate}><fieldset disabled={busy || Boolean(createPending)}><label>{t.category}<select name="category" defaultValue="general">{categories.map((value) => <option key={value} value={value}>{label(value, locale)}</option>)}</select></label>
        <label>{t.subject}<input name="subject" required minLength={3} maxLength={200} /></label><label>{t.description}<textarea name="body" required maxLength={8000} /></label>
        <label>{t.priority}<select name="priority" defaultValue="normal">{priorities.filter((value) => value !== "urgent").map((value) => <option key={value} value={value}>{label(value, locale)}</option>)}</select></label>
        <Files locale={locale} disabled={busy || Boolean(createPending)} files={createFiles} clearKey={createFileKey} onReading={setReadingCreate} change={(files, error) => { setCreateFiles(files); setCreateFileError(Boolean(error)); setCreateError(error ?? ""); }} />
        <button disabled={createFileError || readingCreate}>{t.create}</button></fieldset></form>
      {createPending && <button disabled={busy} onClick={() => { void create(createPending); }}>{t.recoverCreate}</button>}</section>}
    <section className="helpdesk-panel" aria-label={staff ? t.staff : t.mine}><h2>{staff ? t.staff : t.mine}</h2>
      <form aria-label={t.filters} onSubmit={(event) => { event.preventDefault(); const data = new FormData(event.currentTarget); const search = new URLSearchParams(staff ? { limit: "25" } : { limit: "25", queue: "mine" });
        for (const [key, value] of data) if (String(value)) search.set(key, String(value)); setQuery(search.toString()); setLoading(true); void loadList(search.toString()); }}>
        {staff && <label>{t.queue}<select name="queue" disabled={busy} defaultValue="assigned"><option value="assigned">{t.assigned}</option>{canAssign && <option value="unassigned">{t.unassigned}</option>}{admin && <option value="organization">{t.organization}</option>}</select></label>}
        <label>{t.status}<select name="status" disabled={busy}><option value="">{t.all}</option>{statuses.map((value) => <option key={value} value={value}>{label(value, locale)}</option>)}</select></label>
        <label>{t.category}<select name="category" disabled={busy}><option value="">{t.all}</option>{categories.map((value) => <option key={value} value={value}>{label(value, locale)}</option>)}</select></label>
        <label>{t.priority}<select name="priority" disabled={busy}><option value="">{t.all}</option>{priorities.map((value) => <option key={value} value={value}>{label(value, locale)}</option>)}</select></label><button disabled={busy}>{t.apply}</button></form>
      <button disabled={busy} onClick={() => { setLoading(true); void loadList(query); }}>{t.refreshList}</button>{loading ? <p>{t.loading}</p> : !batch?.items.length && <p>{t.empty}</p>}
      {batch?.items.some((item) => item.access === "claim") && <label>{t.assignmentReason}<textarea value={claimReason} disabled={busy || claimPaused} minLength={3} maxLength={500} onChange={(event) => setClaimReason(event.target.value)} /></label>}
      <ul>{batch?.items.map((item) => <li key={item.id}>{item.access === "claim" ? <><p>{item.number}</p><button disabled={busy || readingReply || claimPaused || claimReason.trim().length < 3} onClick={() => { void claim(item); }}>{t.claim}: {item.number}</button></> : <button disabled={busy || readingReply} aria-pressed={ticket?.id === item.id} onClick={() => { void loadTicket(item.id); }}>{item.number}: {item.subject}</button>}
        <p>{label(item.status, locale)} · {label(item.priority, locale)} · {label(item.category, locale)}</p></li>)}</ul>
      {batch?.next_cursor && <button disabled={busy || loading} onClick={() => { setLoading(true); void loadList(`${query}&cursor=${batch.next_cursor}`, true); }}>{t.more}</button>}</section>
    {ticket ? <section className="helpdesk-panel" aria-label={t.details}><h2>{ticket.subject}</h2><p>{ticket.number} · {label(ticket.status, locale)} · {label(ticket.priority, locale)} · {t.version} {ticket.version}</p>
      {ticket.access === "staff" && <p>{t.assignedTo}: {assignees?.items.find((item) => item.id === ticket.assignee_user_id)?.display_name ?? (ticket.assignee_user_id ? ticket.assignee_user_id : t.noAssignee)}</p>}
      <button disabled={busy} onClick={() => { void loadTicket(ticket.id, true); }}>{t.refresh}</button>
      <section aria-label={t.messages}><h3>{t.messages}</h3>{messages && !messages.items.length && <p>{t.noMessages}</p>}
        {messages?.items.map((item) => <article key={item.id} className={item.internal ? "helpdesk-note" : "helpdesk-message"}>{item.internal && <strong>{t.privateNote}</strong>}<p className="helpdesk-prose">{item.body}</p><time>{new Date(item.created_at).toLocaleString(locale)}</time>
          {item.attachments.map((attachment) => <p key={attachment.id}><a href={`${base}/tickets/${ticket.id}/attachments/${attachment.id}`} download>{t.download}: {attachment.filename}</a> ({attachment.size_bytes} B)</p>)}</article>)}
        {messages?.next_cursor && <button disabled={busy} onClick={async () => { setBusy(true); try { const more = await get<MessageList>(`${base}/tickets/${ticket.id}/messages?limit=25&cursor=${messages.next_cursor}`);
          setMessages((old) => old && ({ items: [...old.items, ...more.items.filter((item) => !old.items.some((entry) => entry.id === item.id))], next_cursor: more.next_cursor })); } catch { setMessage(t.error); } finally { setBusy(false); } }}>{t.more}</button>}
      </section>
      {writable && !["closed", "resolved"].includes(ticket.status) && <form aria-label={t.reply} onSubmit={(event) => { event.preventDefault(); void write("messages", { body: reply, internal: staffAccess && internal, attachments: replyFiles }, () => { setReply(""); setReplyFiles([]); setReplyFileKey((old) => old + 1); }); }}>
        <label>{t.reply}<textarea value={reply} required maxLength={8000} disabled={disabled} onChange={(event) => setReply(event.target.value)} /></label>
        {staffAccess && <label className="helpdesk-check"><input type="checkbox" checked={internal} disabled={disabled} onChange={(event) => setInternal(event.target.checked)} />{t.internal}</label>}
        <Files locale={locale} disabled={disabled} files={replyFiles} clearKey={replyFileKey} onReading={setReadingReply} change={(files, error) => { setReplyFiles(files); setReplyError(error ?? ""); }} /><p role="alert">{replyError}</p>
        <button disabled={disabled || readingReply || Boolean(replyError) || !reply.trim()}>{staffAccess && internal ? t.saveNote : t.send}</button></form>}
      {staff && canAssign && ticket.access === "staff" && (admin || ticket.assignee_user_id === userId || !ticket.assignee_user_id) && !["closed", "resolved"].includes(ticket.status) && <form aria-label={t.assign} onSubmit={(event) => { event.preventDefault(); void write("assignment", { assignee_user_id: assignee, reason: assignmentReason }, () => setAssignmentReason("")); }}>
        <label>{t.assignee}<select disabled={disabled} value={assignee} onChange={(event) => setAssignee(event.target.value)}>{assignees?.items.map((item) => <option key={item.id} value={item.id}>{item.display_name}</option>)}</select></label>
        {assignees?.next_cursor && <button type="button" disabled={busy} onClick={async () => { try { const more = await get<AssigneeList>(`${base}/assignees?limit=25&cursor=${assignees.next_cursor}`);
          setAssignees((old) => old && ({ items: [...old.items, ...more.items.filter((item) => !old.items.some((entry) => entry.id === item.id))], next_cursor: more.next_cursor })); } catch { setMessage(t.error); } }}>{t.more}</button>}
        <label>{t.assignmentReason}<textarea required minLength={3} maxLength={500} value={assignmentReason} disabled={disabled} onChange={(event) => setAssignmentReason(event.target.value)} /></label>
        <button disabled={disabled || assignmentReason.trim().length < 3 || assignee === ticket.assignee_user_id}>{t.assign}</button>{!ticket.assignee_user_id && <button type="button" disabled={disabled || assignmentReason.trim().length < 3}
          onClick={() => { void write("assignment", { assignee_user_id: userId, reason: assignmentReason }, () => setAssignmentReason("")); }}>{t.claim}</button>}</form>}
      {((staffAccess && writable) || (ticket.access === "owner" && ticket.status === "resolved")) && allowedStatuses.length > 0 && <form aria-label={t.updateStatus} onSubmit={(event) => { event.preventDefault(); void write("status", { status: choiceStatus, reason: statusReason }, () => setStatusReason("")); }}>
        <label>{t.nextStatus}<select value={choiceStatus} disabled={disabled} onChange={(event) => setNextStatus(event.target.value)}>{allowedStatuses.map((value) => <option key={value} value={value}>{label(value, locale)}</option>)}</select></label>
        <label>{t.statusReason}<textarea required minLength={3} maxLength={500} disabled={disabled} value={statusReason} onChange={(event) => setStatusReason(event.target.value)} /></label>
        <button disabled={disabled || statusReason.trim().length < 3}>{ticket.access === "owner" && ticket.status === "resolved" ? t.close : t.updateStatus}</button></form>}
      {staffAccess && writable && !["closed", "resolved"].includes(ticket.status) && <form aria-label={t.updatePriority} onSubmit={(event) => { event.preventDefault(); void write("priority", { priority: nextPriority, reason: priorityReason }, () => setPriorityReason("")); }}>
        <label>{t.priority}<select disabled={disabled} value={nextPriority} onChange={(event) => setNextPriority(event.target.value)}>{priorities.map((value) => <option key={value} value={value}>{label(value, locale)}</option>)}</select></label>
        <label>{t.priorityReason}<textarea required minLength={3} maxLength={500} disabled={disabled} value={priorityReason} onChange={(event) => setPriorityReason(event.target.value)} /></label><button disabled={disabled || priorityReason.trim().length < 3 || nextPriority === ticket.priority}>{t.updatePriority}</button></form>}
      {(ticket.access === "owner" || admin) && ["resolved", "closed"].includes(ticket.status) && <form aria-label={t.reopen} onSubmit={(event) => { event.preventDefault(); void write("reopen", { reason: reopenReason }, () => setReopenReason("")); }}>
        <label>{t.reopenReason}<textarea required minLength={3} maxLength={500} disabled={disabled} value={reopenReason} onChange={(event) => setReopenReason(event.target.value)} /></label><button disabled={disabled || reopenReason.trim().length < 3}>{t.reopen}</button></form>}
      <section aria-label={t.history}><h3>{t.history}</h3>{history && !history.items.length && <p>{t.noHistory}</p>}<ol>{history?.items.map((item) => <li key={item.id}><p>{label(item.event, locale)} · {label(item.status, locale)} · {label(item.priority, locale)} · {t.version} {item.version}</p>{item.reason && <p className="helpdesk-prose">{item.reason}</p>}<time>{new Date(item.created_at).toLocaleString(locale)}</time></li>)}</ol>
        {history?.next_cursor && <button disabled={busy} onClick={async () => { setBusy(true); try { const more = await get<HistoryList>(`${base}/tickets/${ticket.id}/history?limit=25&cursor=${history.next_cursor}`);
          setHistory((old) => old && ({ items: [...old.items, ...more.items.filter((item) => !old.items.some((entry) => entry.id === item.id))], next_cursor: more.next_cursor })); } catch { setMessage(t.error); } finally { setBusy(false); } }}>{t.more}</button>}</section>
    </section> : <p>{t.chooseTicket}</p>}
    <Notices base={base} locale={locale} open={(id) => { void loadTicket(id); }} />
  </div>;
}
