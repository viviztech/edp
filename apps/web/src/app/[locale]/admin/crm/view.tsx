"use client";

import { useCallback, useEffect, useState } from "react";
import type { components } from "../../../../lib/api-contracts";
import { crmMessages, type CrmLocale } from "../../../../lib/crm-messages";
import CrmExports from "./exports";

type Lead = components["schemas"]["LeadView"];
type Activity = components["schemas"]["ActivityView"];
type Review = components["schemas"]["DuplicateReviewView"];
type RegistrationLink = components["schemas"]["LeadConversionView"];
type Tag = components["schemas"]["TagView"];
type LeadStatus = Lead["status"];
const statuses: LeadStatus[] = ["new", "contacted", "interested", "registration_started", "not_interested"];
const uuidPattern = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";

export default function CrmWorkspace({ org, permissions, locale }: { org: string; permissions: string[]; locale: CrmLocale }) {
  const text = crmMessages[locale];
  const root = `/api/crm/organizations/${org}`;
  const [items, setItems] = useState<Lead[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [selected, setSelected] = useState<Lead | null>(null);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [registration, setRegistration] = useState<RegistrationLink | null>(null);
  const [orgTags, setOrgTags] = useState<Tag[]>([]);
  const [leadTags, setLeadTags] = useState<Tag[]>([]);
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [newTag, setNewTag] = useState("");
  const [tagChoice, setTagChoice] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [creating, setCreating] = useState(false);
  const [newLead, setNewLead] = useState({ name: "", email: "", phone: "", source: "manual", campaign: "", notes: "" });
  const [edit, setEdit] = useState({ status: "new" as LeadStatus, assigned_user_id: "", notes: "" });
  const [activity, setActivity] = useState({ activity_type: "call", note: "", due_at: "" });
  const [duplicate, setDuplicate] = useState({ candidate: "", survivor: "", reason: "" });
  const [person, setPerson] = useState({ id: "", reason: "" });
  const allowed = (permission: string) => permissions.includes(permission);
  const canMerge = permissions.includes("crm.lead.merge");
  const canViewTags = permissions.includes("crm.tag.view");

  const api = useCallback(async <T,>(path: string, method = "GET", data?: unknown): Promise<T> => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (method !== "GET") {
      const csrf = await fetch("/api/session/csrf", { cache: "no-store" });
      if (!csrf.ok) throw new Error(text.error);
      headers["x-csrf-token"] = (await csrf.json()).csrf_token;
    }
    const response = await fetch(path, { method, headers, body: data === undefined ? undefined : JSON.stringify(data), cache: "no-store" });
    if (!response.ok) throw new Error(response.status === 409 ? text.conflict : text.error);
    if (response.status === 204) return undefined as T;
    return response.json();
  }, [text.conflict, text.error]);

  async function run(work: () => Promise<void>) {
    setBusy(true);
    setMessage("");
    try { await work(); } catch (error) { setMessage(error instanceof Error ? error.message : text.error); } finally { setBusy(false); }
  }

  async function loadQueue(more = false, overdue = overdueOnly) {
    const query = new URLSearchParams();
    if (more && cursor) query.set("cursor", cursor);
    if (overdue) query.set("overdue", "true");
    const page = await api<components["schemas"]["LeadList"]>(`${root}/leads${query.size ? `?${query}` : ""}`);
    setItems((current) => more ? [...current, ...page.items] : page.items);
    setCursor(page.next_cursor ?? null);
  }

  async function loadReviews() {
    if (!canMerge) return;
    const page = await api<components["schemas"]["DuplicateReviewList"]>(`${root}/duplicate-reviews`);
    setReviews(page.items);
  }

  useEffect(() => {
    let active = true;
    Promise.all([
      api<components["schemas"]["LeadList"]>(`${root}/leads`),
      canMerge ? api<components["schemas"]["DuplicateReviewList"]>(`${root}/duplicate-reviews`) : Promise.resolve({ items: [], next_cursor: null }),
      canViewTags ? api<components["schemas"]["TagList"]>(`${root}/tags`) : Promise.resolve({ items: [] }),
    ])
      .then(([leadPage, reviewPage, tagPage]) => { if (active) { setItems(leadPage.items); setCursor(leadPage.next_cursor ?? null); setReviews(reviewPage.items); setOrgTags(tagPage.items); } })
      .catch(() => { if (active) setMessage(text.error); });
    return () => { active = false; };
  }, [api, canMerge, canViewTags, root, text.error]);

  async function choose(lead: Lead) {
    setSelected(lead);
    setEdit({ status: lead.status, assigned_user_id: lead.assigned_user_id ?? "", notes: lead.notes });
    setRegistration(null);
    setPerson({ id: "", reason: "" });
    const activityPromise = api<components["schemas"]["ActivityList"]>(`${root}/leads/${lead.id}/activities`);
    const registrationPromise = fetch(`${root}/leads/${lead.id}/registration-link`, { cache: "no-store" }).then(async (response) => response.status === 404 ? null : response.ok ? response.json() as Promise<RegistrationLink> : Promise.reject(new Error(text.error)));
    const tagsPromise = canViewTags
      ? api<components["schemas"]["TagList"]>(`${root}/leads/${lead.id}/tags`)
      : Promise.resolve({ items: [] });
    const [activityPage, link, tagPage] = await Promise.all([activityPromise, registrationPromise, tagsPromise]);
    setActivities(activityPage.items);
    setRegistration(link);
    setLeadTags(tagPage.items);
    setTagChoice("");
  }

  function replaceLead(lead: Lead) {
    setSelected(lead);
    setEdit({ status: lead.status, assigned_user_id: lead.assigned_user_id ?? "", notes: lead.notes });
    setItems((current) => current.map((item) => item.id === lead.id ? lead : item));
    setMessage(text.saved);
  }

  return <div className="crm-workspace" aria-busy={busy}>
    <aside className="crm-queue">
      <div className="crm-section-title"><div><p className="eyebrow">{text.queue}</p><strong>{items.length}</strong></div><div className="actions"><button aria-pressed={overdueOnly} disabled={busy} onClick={() => { const next = !overdueOnly; setOverdueOnly(next); run(() => loadQueue(false, next)); }}>{overdueOnly ? text.allLeads : text.overdueOnly}</button><button disabled={busy || !allowed("crm.lead.create")} onClick={() => setCreating(true)}>{text.newLead}</button><button disabled={busy} onClick={() => run(() => loadQueue())}>{text.refresh}</button></div></div>
      {creating ? <form className="crm-create" onSubmit={(event) => { event.preventDefault(); run(async () => { const lead = await api<Lead>(`${root}/leads`, "POST", newLead); setItems((current) => [lead, ...current]); setCreating(false); setNewLead({ name: "", email: "", phone: "", source: "manual", campaign: "", notes: "" }); await choose(lead); }); }}>
        <label>{text.name}<input required maxLength={120} value={newLead.name} onChange={(event) => setNewLead({ ...newLead, name: event.target.value })} /></label>
        <label>{text.email}<input type="email" maxLength={320} value={newLead.email} onChange={(event) => setNewLead({ ...newLead, email: event.target.value })} /></label>
        <label>{text.phone}<input maxLength={32} value={newLead.phone} onChange={(event) => setNewLead({ ...newLead, phone: event.target.value })} /></label>
        <label>{text.source}<input maxLength={80} value={newLead.source} onChange={(event) => setNewLead({ ...newLead, source: event.target.value })} /></label>
        <label>{text.campaign}<input maxLength={120} value={newLead.campaign} onChange={(event) => setNewLead({ ...newLead, campaign: event.target.value })} /></label>
        <div className="actions"><button type="submit" disabled={busy}>{text.create}</button><button type="button" onClick={() => setCreating(false)}>{text.cancel}</button></div>
      </form> : null}
      {items.length === 0 ? <p>{text.empty}</p> : <ol className="crm-leads">{items.map((lead) => <li key={lead.id}><button aria-pressed={selected?.id === lead.id} disabled={busy} onClick={() => run(() => choose(lead))}><span><strong>{lead.name}</strong><small>{lead.source}{lead.campaign ? ` ? ${lead.campaign}` : ""}</small></span><span className={`crm-status crm-status-${lead.status}`}>{text[lead.status]}</span></button></li>)}</ol>}
      {cursor ? <button disabled={busy} onClick={() => run(() => loadQueue(true))}>{text.more}</button> : null}
    </aside>

    <section className="crm-record">
      <p className="crm-message" role="status">{busy ? text.loading : message}</p>
      {!selected ? <div className="crm-empty"><span aria-hidden="true">?</span><p>{text.queueHint}</p></div> : <>
        <header className="crm-record-header"><div><p className="eyebrow">{selected.source}</p><h2>{selected.name}</h2><p>{selected.email || selected.phone || selected.id}</p></div><span className={`crm-status crm-status-${selected.status}`}>{text[selected.status]}</span></header>
        <div className="crm-record-grid">
          <section className="crm-panel"><h3>{text.status}</h3><form className="crm-form" onSubmit={(event) => { event.preventDefault(); run(async () => replaceLead(await api<Lead>(`${root}/leads/${selected.id}`, "PATCH", { status: edit.status, assigned_user_id: edit.assigned_user_id || null, notes: edit.notes, expected_version: selected.version }))); }}>
            <label>{text.status}<select value={edit.status} disabled={selected.status === "merged" || selected.status === "converted"} onChange={(event) => setEdit({ ...edit, status: event.target.value as LeadStatus })}>{statuses.map((status) => <option key={status} value={status}>{text[status]}</option>)}</select></label>
            <label>{text.assignee}<input pattern={uuidPattern} value={edit.assigned_user_id} onChange={(event) => setEdit({ ...edit, assigned_user_id: event.target.value })} /></label>
            <label>{text.notes}<textarea rows={5} maxLength={5000} value={edit.notes} onChange={(event) => setEdit({ ...edit, notes: event.target.value })} /></label>
            <button disabled={busy || !allowed("crm.lead.update") || selected.status === "merged" || selected.status === "converted"}>{text.save}</button>
          </form></section>

          {canViewTags ? <section className="crm-panel crm-tags-panel"><h3>{text.tags}</h3>
            {leadTags.length === 0 ? <p>{text.noTags}</p> : <ul className="crm-tags">{leadTags.map((tag) => <li key={tag.id}><span>{tag.name}</span>{allowed("crm.tag.manage") ? <button aria-label={`${text.removeTag} ${tag.name}`} disabled={busy} onClick={() => run(async () => { await api(`${root}/leads/${selected.id}/tags/${tag.id}/detach`, "POST", {}); setLeadTags((current) => current.filter((item) => item.id !== tag.id)); })}>×</button> : null}</li>)}</ul>}
            {allowed("crm.tag.manage") ? <><form className="crm-form crm-tag-form" onSubmit={(event) => { event.preventDefault(); run(async () => { const tag = await api<Tag>(`${root}/tags`, "POST", { name: newTag }); setOrgTags((current) => [...current, tag].sort((a, b) => a.name.localeCompare(b.name))); setNewTag(""); }); }}><label>{text.tagName}<input required maxLength={40} value={newTag} onChange={(event) => setNewTag(event.target.value)} /></label><button disabled={busy}>{text.addTag}</button></form>
            <form className="crm-form crm-tag-form" onSubmit={(event) => { event.preventDefault(); run(async () => { const tag = await api<Tag>(`${root}/leads/${selected.id}/tags/${tagChoice}/attach`, "POST", {}); setLeadTags((current) => [...current, tag].sort((a, b) => a.name.localeCompare(b.name))); setTagChoice(""); }); }}><label>{text.tags}<select required value={tagChoice} onChange={(event) => setTagChoice(event.target.value)}><option value="">—</option>{orgTags.filter((tag) => !leadTags.some((item) => item.id === tag.id)).map((tag) => <option key={tag.id} value={tag.id}>{tag.name}</option>)}</select></label><button disabled={busy || !tagChoice}>{text.attachTag}</button></form></> : null}
          </section> : null}

          <section className="crm-panel"><h3>{text.activities}</h3><form className="crm-form" onSubmit={(event) => { event.preventDefault(); run(async () => { const item = await api<Activity>(`${root}/leads/${selected.id}/activities`, "POST", { activity_type: activity.activity_type, note: activity.note, due_at: activity.due_at ? new Date(activity.due_at).toISOString() : null }); setActivities((current) => [item, ...current]); setActivity({ activity_type: "call", note: "", due_at: "" }); }); }}>
            <label>{text.activityType}<select value={activity.activity_type} onChange={(event) => setActivity({ ...activity, activity_type: event.target.value })}>{["call", "email", "meeting", "task", "note"].map((type) => <option key={type} value={type}>{type === "email" ? text.email : text[type as keyof typeof text]}</option>)}</select></label>
            <label>{text.activityNote}<textarea required rows={3} maxLength={5000} value={activity.note} onChange={(event) => setActivity({ ...activity, note: event.target.value })} /></label>
            <label>{text.due}<input type="datetime-local" value={activity.due_at} onChange={(event) => setActivity({ ...activity, due_at: event.target.value })} /></label>
            <button disabled={busy || !allowed("crm.activity.create")}>{text.addActivity}</button>
          </form>
          {activities.length === 0 ? <p>{text.noActivities}</p> : <ol className="crm-timeline">{activities.map((item) => <li key={item.id}><span>{item.activity_type}</span><p>{item.note}</p>{item.due_at ? <time dateTime={item.due_at}>{new Date(item.due_at).toLocaleString(locale)}</time> : null}{item.completed_at ? <strong className="crm-completed">{text.completed}</strong> : allowed("crm.activity.update") ? <button disabled={busy} onClick={() => run(async () => { const updated = await api<Activity>(`${root}/leads/${selected.id}/activities/${item.id}/complete`, "POST", { expected_version: item.version }); setActivities((current) => current.map((entry) => entry.id === updated.id ? updated : entry)); })}>{text.complete}</button> : null}</li>)}</ol>}</section>

          {allowed("crm.lead.convert") ? <section className="crm-panel"><h3>{text.registration}</h3>{registration ? <p className="crm-success">{text.linked}<br /><code>{registration.person_id}</code></p> : <form className="crm-form" onSubmit={(event) => { event.preventDefault(); run(async () => { const link = await api<RegistrationLink>(`${root}/leads/${selected.id}/registration-link`, "POST", { person_id: person.id, reason: person.reason, expected_version: selected.version }); setRegistration(link); replaceLead({ ...selected, status: "registration_started", version: selected.version + 1 }); }); }}>
            <label>{text.person}<input required pattern={uuidPattern} value={person.id} onChange={(event) => setPerson({ ...person, id: event.target.value })} /></label>
            <label>{text.reviewReason}<textarea required maxLength={500} value={person.reason} onChange={(event) => setPerson({ ...person, reason: event.target.value })} /></label>
            <button disabled={busy}>{text.linkPerson}</button>
          </form>}</section> : null}

          {allowed("crm.lead.merge") ? <section className="crm-panel"><h3>{text.duplicate}</h3><form className="crm-form" onSubmit={(event) => { event.preventDefault(); run(async () => { const review = await api<Review>(`${root}/duplicate-reviews`, "POST", { lead_a_id: selected.id, lead_b_id: duplicate.candidate }); setReviews((current) => [review, ...current]); }); }}><label>{text.candidate}<input required pattern={uuidPattern} value={duplicate.candidate} onChange={(event) => setDuplicate({ ...duplicate, candidate: event.target.value })} /></label><button disabled={busy}>{text.openReview}</button></form>
            <h4>{text.reviews}</h4><label>{text.survivor}<input pattern={uuidPattern} value={duplicate.survivor} onChange={(event) => setDuplicate({ ...duplicate, survivor: event.target.value })} /></label><label>{text.reviewReason}<input maxLength={500} value={duplicate.reason} onChange={(event) => setDuplicate({ ...duplicate, reason: event.target.value })} /></label>
            <ul className="crm-reviews">{reviews.filter((review) => review.lead_a_id === selected.id || review.lead_b_id === selected.id).map((review) => <li key={review.id}><code>{review.lead_a_id.slice(0, 8)} / {review.lead_b_id.slice(0, 8)}</code><span>{review.state}</span>{review.state === "pending" ? <div className="actions"><button disabled={!duplicate.reason || !duplicate.survivor} onClick={() => run(async () => { await api(`${root}/duplicate-reviews/${review.id}/resolve`, "POST", { action: "merge", survivor_id: duplicate.survivor, reason: duplicate.reason, expected_version: review.version }); await Promise.all([loadQueue(), loadReviews()]); })}>{text.merge}</button><button disabled={!duplicate.reason} onClick={() => run(async () => { await api(`${root}/duplicate-reviews/${review.id}/resolve`, "POST", { action: "reject", survivor_id: null, reason: duplicate.reason, expected_version: review.version }); await loadReviews(); })}>{text.reject}</button></div> : null}</li>)}</ul>
          </section> : null}
        </div>
      </>}

      {allowed("crm.lead.export") ? <CrmExports key={org} org={org} locale={locale} blocked={busy} /> : null}
    </section>
  </div>;
}
