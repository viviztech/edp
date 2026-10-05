"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import type { components } from "../../../../lib/api-contracts";
import { mentoringMessages } from "../../../../lib/mentoring-messages";

type Locale = "en" | "ta";
type Workspace = components["schemas"]["Workspace"];
const empty: Workspace = { mentor_candidates: [], enrollment_candidates: [], profiles: [], expertise: [],
  availability: [], assignments: [], sessions: [], notes: [], goals: [], action_items: [],
  follow_ups: [], feedback_count: 0, average_rating: null };

export default function MentoringWorkspace({ org, locale, canAdmin }: {
  org: string; locale: Locale; canAdmin: boolean;
}) {
  const text = mentoringMessages[locale];
  const root = `/api/mentoring/organizations/${org}`;
  const [data, setData] = useState<Workspace>(empty);
  const [busy, setBusy] = useState(true);
  const [message, setMessage] = useState(text.loading as string);
  const activeAssignments = data.assignments.filter((item) => item.state === "active");

  const load = useCallback(async () => {
    const response = await fetch(root + "/workspace", { cache: "no-store" });
    if (!response.ok) throw new Error("request_failed");
    setData(await response.json() as Workspace);
  }, [root]);
  useEffect(() => { let active = true; (async () => {
    try { await load(); if (active) setMessage(""); }
    catch { if (active) setMessage(text.error); }
    finally { if (active) setBusy(false); }
  })(); return () => { active = false; }; }, [load, text.error]);

  async function command(path: string, body: object) {
    setBusy(true);
    try {
      const csrf = await fetch("/api/session/csrf", { cache: "no-store" });
      if (!csrf.ok) throw new Error("csrf_failed");
      const response = await fetch(root + path, { method: "POST", headers: {
        "Content-Type": "application/json",
        "x-csrf-token": (await csrf.json() as { csrf_token: string }).csrf_token,
      }, body: JSON.stringify(body) });
      if (!response.ok) throw new Error("request_failed");
      await load(); setMessage(text.saved); return true;
    } catch { setMessage(text.error); return false; }
    finally { setBusy(false); }
  }
  const values = (event: FormEvent<HTMLFormElement>) => Object.fromEntries(new FormData(event.currentTarget));
  const iso = (value: FormDataEntryValue) => new Date(String(value)).toISOString();

  return <section aria-busy={busy}>
    <p role="status">{busy ? text.loading : message}</p>
    {canAdmin && <div className="program-grid">
      <section className="program-panel"><h2>{text.createProfile}</h2>
        <form onSubmit={(event) => { event.preventDefault(); const v = values(event); void command("/profiles", {
          user_id: v.user_id, headline: v.headline, biography: v.biography || null,
        }); }}><label>Mentor<select name="user_id" required><option value="">Select</option>
          {data.mentor_candidates.filter((item) => !item.has_profile).map((item) =>
            <option key={item.user_id} value={item.user_id}>{item.display_name}</option>)}</select></label>
          <label>Headline<input name="headline" minLength={2} maxLength={160} required /></label>
          <label>Biography<textarea name="biography" maxLength={4000} /></label>
          <button disabled={busy} type="submit">{text.submit}</button></form></section>
      <section className="program-panel"><h2>{text.expertise}</h2>
        <form onSubmit={(event) => { event.preventDefault(); const v = values(event); void command("/expertise", {
          mentor_profile_id: v.profile, code: v.code, name_en: v.name_en, name_ta: v.name_ta,
        }); }}><ProfileSelect profiles={data.profiles} /><label>Code<input name="code" pattern="[a-z][a-z0-9_-]*" required /></label>
          <label>Name (English)<input name="name_en" required /></label><label>Name (Tamil)<input name="name_ta" required /></label>
          <button disabled={busy} type="submit">{text.submit}</button></form></section>
      <section className="program-panel"><h2>{text.availability}</h2>
        <form onSubmit={(event) => { event.preventDefault(); const v = values(event); void command("/availability", {
          mentor_profile_id: v.profile, weekday: Number(v.weekday), starts_at: v.starts_at,
          ends_at: v.ends_at, timezone: "Asia/Kolkata",
        }); }}><ProfileSelect profiles={data.profiles} /><label>Weekday<select name="weekday">
          {["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].map((day, index) =>
            <option key={day} value={index}>{day}</option>)}</select></label>
          <label>From<input name="starts_at" type="time" required /></label><label>To<input name="ends_at" type="time" required /></label>
          <button disabled={busy} type="submit">{text.submit}</button></form></section>
      <section className="program-panel"><h2>{text.assign}</h2>
        <form onSubmit={(event) => { event.preventDefault(); const v = values(event); void command("/assignments", {
          mentor_profile_id: v.profile, enrollment_id: v.enrollment, starts_on: v.starts_on,
          ends_on: v.ends_on || null, reason: v.reason,
        }); }}><ProfileSelect profiles={data.profiles} /><label>Participant<select name="enrollment" required><option value="">Select</option>
          {data.enrollment_candidates.filter((item) => !item.has_active_assignment).map((item) =>
            <option key={item.enrollment_id} value={item.enrollment_id}>{item.participant_name}</option>)}</select></label>
          <label>Starts<input name="starts_on" type="date" required /></label><label>Ends<input name="ends_on" type="date" /></label>
          <label>Reason<input name="reason" minLength={3} required /></label><button disabled={busy} type="submit">{text.assign}</button></form></section>
    </div>}

    <div className="program-grid">
      <section className="program-panel"><h2>{text.schedule}</h2>
        <form onSubmit={(event) => { event.preventDefault(); const v = values(event); void command("/sessions", {
          assignment_id: v.assignment, starts_at: iso(v.starts_at), ends_at: iso(v.ends_at), mode: v.mode,
          location_or_link: v.location || null, topic: v.topic,
        }); }}><AssignmentSelect items={activeAssignments} /><label>Topic<input name="topic" required /></label>
          <label>Starts<input name="starts_at" type="datetime-local" required /></label><label>Ends<input name="ends_at" type="datetime-local" required /></label>
          <label>Mode<select name="mode"><option value="online">Online</option><option value="in_person">In person</option><option value="phone">Phone</option></select></label>
          <label>Location or link<input name="location" /></label><button disabled={busy} type="submit">{text.schedule}</button></form></section>
      <section className="program-panel"><h2>{text.notes}</h2>
        <form onSubmit={(event) => { event.preventDefault(); const v = values(event); void command("/notes", {
          assignment_id: v.assignment, session_id: v.session || null, visibility: v.visibility, body: v.body,
        }); }}><AssignmentSelect items={activeAssignments} /><label>Session<select name="session"><option value="">General</option>{data.sessions.map((item) => <option key={item.id} value={item.id}>{item.topic}</option>)}</select></label>
          <label>Visibility<select name="visibility"><option value="mentor_private">{text.privateNote}</option><option value="shared_with_participant">{text.sharedNote}</option></select></label>
          <label>Note<textarea name="body" minLength={1} required /></label><button disabled={busy} type="submit">{text.submit}</button></form></section>
      <section className="program-panel"><h2>{text.goals}</h2>
        <form onSubmit={(event) => { event.preventDefault(); const v = values(event); void command("/goals", {
          assignment_id: v.assignment, title: v.title, description: v.description || null, target_date: v.target_date || null,
        }); }}><AssignmentSelect items={activeAssignments} /><label>Goal<input name="title" required /></label><label>Description<textarea name="description" /></label>
          <label>Target date<input name="target_date" type="date" /></label><button disabled={busy} type="submit">{text.submit}</button></form></section>
      <section className="program-panel"><h2>{text.actions}</h2>
        <form onSubmit={(event) => { event.preventDefault(); const v = values(event); void command("/action-items", {
          assignment_id: v.assignment, goal_id: v.goal || null, title: v.title, due_at: v.due_at ? iso(v.due_at) : null,
        }); }}><AssignmentSelect items={activeAssignments} /><label>Goal<select name="goal"><option value="">None</option>{data.goals.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>
          <label>Action<input name="title" required /></label><label>Due<input name="due_at" type="datetime-local" /></label><button disabled={busy} type="submit">{text.submit}</button></form></section>
      <section className="program-panel"><h2>{text.followUps}</h2>
        <form onSubmit={(event) => { event.preventDefault(); const v = values(event); void command("/follow-ups", {
          assignment_id: v.assignment, session_id: v.session || null, purpose: v.purpose, due_at: iso(v.due_at),
        }); }}><AssignmentSelect items={activeAssignments} /><label>Session<select name="session"><option value="">General</option>{data.sessions.map((item) => <option key={item.id} value={item.id}>{item.topic}</option>)}</select></label>
          <label>Purpose<input name="purpose" required /></label><label>Due<input name="due_at" type="datetime-local" required /></label><button disabled={busy} type="submit">{text.submit}</button></form></section>
    </div>

    <section className="program-panel"><h2>{text.assignments}</h2><ul className="program-list">{data.assignments.map((item) => <li key={item.id}>
      <strong>{item.participant_name}</strong><span>{item.mentor_name}</span><span className={`program-state program-state-${item.state}`}>{item.state}</span>
      {canAdmin && item.state === "active" && <button disabled={busy} onClick={() => void command(`/assignments/${item.id}/end`, { expected_version: item.version, reason: "Mentoring assignment concluded" })}>{text.end}</button>}
    </li>)}</ul></section>
    <section className="program-panel"><h2>{text.sessions}</h2><ul className="program-list">{data.sessions.map((item) => <li key={item.id}>
      <strong>{item.topic}</strong><span>{new Date(item.starts_at).toLocaleString(locale)}</span><span>{item.status}</span>
      {item.status === "scheduled" && <div><button disabled={busy} onClick={() => void command(`/sessions/${item.id}/state`, { expected_version: item.version, target: "completed", reason: "Session outcomes recorded" })}>{text.complete}</button>
        <button disabled={busy} onClick={() => void command(`/sessions/${item.id}/state`, { expected_version: item.version, target: "cancelled", reason: "Session cancelled by mentor" })}>{text.cancel}</button></div>}
    </li>)}</ul></section>
    <section className="program-panel"><h2>{text.goals}</h2><ul className="program-list">{data.goals.map((item) => <li key={item.id}><strong>{item.title}</strong><span>{item.progress_percent}%</span><span>{item.state}</span></li>)}</ul></section>
    <section className="program-panel"><h2>{text.actions}</h2><ul className="program-list">{data.action_items.map((item) => <li key={item.id}><strong>{item.title}</strong><span>{item.state}</span>{item.state === "open" && <button onClick={() => void command(`/action-items/${item.id}/state`, { expected_version: item.version, target: "completed", reason: "Action reviewed as complete" })}>{text.complete}</button>}</li>)}</ul></section>
    <section className="program-panel"><h2>{text.followUps}</h2><ul className="program-list">{data.follow_ups.map((item) => <li key={item.id}><strong>{item.purpose}</strong><span>{new Date(item.due_at).toLocaleString(locale)}</span>{item.overdue && <span role="alert">{text.overdue}</span>}{item.state === "scheduled" && <button onClick={() => void command(`/follow-ups/${item.id}/state`, { expected_version: item.version, target: "completed", reason: "Follow-up completed" })}>{text.complete}</button>}</li>)}</ul>
      <p>{text.feedback}: {data.feedback_count}{data.average_rating !== null ? ` · ${data.average_rating}/5` : ""}</p></section>
  </section>;
}

function ProfileSelect({ profiles }: { profiles: Workspace["profiles"] }) {
  return <label>Mentor<select name="profile" required><option value="">Select</option>{profiles.filter((item) => item.state === "active").map((item) => <option key={item.id} value={item.id}>{item.display_name}</option>)}</select></label>;
}
function AssignmentSelect({ items }: { items: Workspace["assignments"] }) {
  return <label>Participant<select name="assignment" required><option value="">Select</option>{items.map((item) => <option key={item.id} value={item.id}>{item.participant_name} · {item.mentor_name}</option>)}</select></label>;
}
