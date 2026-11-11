"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import type { components } from "../../../../lib/api-contracts";
import { mentoringMessages } from "../../../../lib/mentoring-messages";
import { Card } from "../../../../components/ui/card";
import { Button } from "../../../../components/ui/button";
import { Input } from "../../../../components/ui/input";
import { Textarea } from "../../../../components/ui/textarea";

type Locale = "en" | "ta";
type Workspace = components["schemas"]["Workspace"];
const empty: Workspace = { mentor_candidates: [], enrollment_candidates: [], profiles: [], expertise: [],
  availability: [], assignments: [], sessions: [], notes: [], goals: [], action_items: [],
  follow_ups: [], feedback_count: 0, average_rating: null };
const fields = {
  en: { mentor: "Mentor", select: "Select", headline: "Headline", biography: "Biography", code: "Code", english: "Name (English)", tamil: "Name (Tamil)", weekday: "Weekday", from: "From", to: "To", participant: "Participant", starts: "Starts", ends: "Ends", reason: "Reason", topic: "Topic", mode: "Mode", online: "Online", inPerson: "In person", phone: "Phone", location: "Location or link", session: "Session", general: "General", visibility: "Visibility", note: "Note", goal: "Goal", description: "Description", targetDate: "Target date", none: "None", action: "Action", due: "Due", purpose: "Purpose", days: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"] },
  ta: { mentor: "வழிகாட்டி", select: "தேர்ந்தெடுக்கவும்", headline: "தலைப்பு", biography: "வாழ்க்கைக் குறிப்பு", code: "குறியீடு", english: "பெயர் (ஆங்கிலம்)", tamil: "பெயர் (தமிழ்)", weekday: "வார நாள்", from: "தொடக்கம்", to: "முடிவு", participant: "பங்கேற்பாளர்", starts: "தொடக்கம்", ends: "முடிவு", reason: "காரணம்", topic: "தலைப்பு", mode: "முறை", online: "இணையவழி", inPerson: "நேரில்", phone: "தொலைபேசி", location: "இடம் அல்லது இணைப்பு", session: "அமர்வு", general: "பொது", visibility: "பார்வை அனுமதி", note: "குறிப்பு", goal: "இலக்கு", description: "விளக்கம்", targetDate: "இலக்கு தேதி", none: "இல்லை", action: "செயல்", due: "கெடு", purpose: "நோக்கம்", days: ["திங்கள்", "செவ்வாய்", "புதன்", "வியாழன்", "வெள்ளி", "சனி", "ஞாயிறு"] },
} as const;

export default function MentoringWorkspace({ org, locale, canAdmin }: {
  org: string; locale: Locale; canAdmin: boolean;
}) {
  const text = mentoringMessages[locale];
  const f = fields[locale];
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

  return <section className="mentor-workspace" aria-busy={busy}>
    {(busy || message) && <p className="mentor-feedback" role="status">{busy ? text.loading : message}</p>}
    <nav className="mentor-section-nav" aria-label={locale === "ta" ? "வழிகாட்டுதல் பகுதிகள்" : "Mentoring sections"}>
      {canAdmin && <a href="#mentor-setup">{locale === "ta" ? "வழிகாட்டி அமைப்பு" : "Mentor setup"}</a>}
      <a href="#mentor-work">{locale === "ta" ? "அமர்வுகள் மற்றும் செயல்கள்" : "Sessions and actions"}</a>
      <a href="#mentor-activity">{locale === "ta" ? "நடப்பு பதிவுகள்" : "Current records"}</a>
    </nav>
    {canAdmin && <div id="mentor-setup" className="mentor-group"><h2>{locale === "ta" ? "வழிகாட்டி அமைப்பு" : "Mentor setup"}</h2><div className="program-grid">
      <Card className="program-panel"><h2>{text.createProfile}</h2>
        <form onSubmit={(event) => { event.preventDefault(); const v = values(event); void command("/profiles", {
          user_id: v.user_id, headline: v.headline, biography: v.biography || null,
        }); }}><label>{f.mentor}<select name="user_id" required><option value="">{f.select}</option>
          {data.mentor_candidates.filter((item) => !item.has_profile).map((item) =>
            <option key={item.user_id} value={item.user_id}>{item.display_name}</option>)}</select></label>
          <label>{f.headline}<Input name="headline" minLength={2} maxLength={160} required /></label>
          <label>{f.biography}<Textarea name="biography" maxLength={4000} /></label>
          <Button disabled={busy} type="submit">{text.submit}</Button></form></Card>
      <Card className="program-panel"><h2>{text.expertise}</h2>
        <form onSubmit={(event) => { event.preventDefault(); const v = values(event); void command("/expertise", {
          mentor_profile_id: v.profile, code: v.code, name_en: v.name_en, name_ta: v.name_ta,
        }); }}><ProfileSelect profiles={data.profiles} locale={locale} /><label>{f.code}<Input name="code" pattern="[a-z][a-z0-9_-]*" required /></label>
          <label>{f.english}<Input name="name_en" required /></label><label>{f.tamil}<Input name="name_ta" required /></label>
          <Button disabled={busy} type="submit">{text.submit}</Button></form></Card>
      <Card className="program-panel"><h2>{text.availability}</h2>
        <form onSubmit={(event) => { event.preventDefault(); const v = values(event); void command("/availability", {
          mentor_profile_id: v.profile, weekday: Number(v.weekday), starts_at: v.starts_at,
          ends_at: v.ends_at, timezone: "Asia/Kolkata",
        }); }}><ProfileSelect profiles={data.profiles} locale={locale} /><label>{f.weekday}<select name="weekday">
          {f.days.map((day, index) =>
            <option key={day} value={index}>{day}</option>)}</select></label>
          <label>{f.from}<Input name="starts_at" type="time" required /></label><label>{f.to}<Input name="ends_at" type="time" required /></label>
          <Button disabled={busy} type="submit">{text.submit}</Button></form></Card>
      <Card className="program-panel"><h2>{text.assign}</h2>
        <form onSubmit={(event) => { event.preventDefault(); const v = values(event); void command("/assignments", {
          mentor_profile_id: v.profile, enrollment_id: v.enrollment, starts_on: v.starts_on,
          ends_on: v.ends_on || null, reason: v.reason,
        }); }}><ProfileSelect profiles={data.profiles} locale={locale} /><label>{f.participant}<select name="enrollment" required><option value="">{f.select}</option>
          {data.enrollment_candidates.filter((item) => !item.has_active_assignment).map((item) =>
            <option key={item.enrollment_id} value={item.enrollment_id}>{item.participant_name}</option>)}</select></label>
          <label>{f.starts}<Input name="starts_on" type="date" required /></label><label>{f.ends}<Input name="ends_on" type="date" /></label>
          <label>{f.reason}<Input name="reason" minLength={3} required /></label><Button disabled={busy} type="submit">{text.assign}</Button></form></Card>
    </div></div>}

    <div id="mentor-work" className="mentor-group"><h2>{locale === "ta" ? "அமர்வுகள் மற்றும் செயல்கள்" : "Sessions and actions"}</h2><div className="program-grid">
      <Card className="program-panel"><h2>{text.schedule}</h2>
        <form onSubmit={(event) => { event.preventDefault(); const v = values(event); void command("/sessions", {
          assignment_id: v.assignment, starts_at: iso(v.starts_at), ends_at: iso(v.ends_at), mode: v.mode,
          location_or_link: v.location || null, topic: v.topic,
        }); }}><AssignmentSelect items={activeAssignments} locale={locale} /><label>{f.topic}<Input name="topic" required /></label>
          <label>{f.starts}<Input name="starts_at" type="datetime-local" required /></label><label>{f.ends}<Input name="ends_at" type="datetime-local" required /></label>
          <label>{f.mode}<select name="mode"><option value="online">{f.online}</option><option value="in_person">{f.inPerson}</option><option value="phone">{f.phone}</option></select></label>
          <label>{f.location}<Input name="location" /></label><Button disabled={busy} type="submit">{text.schedule}</Button></form></Card>
      <Card className="program-panel"><h2>{text.notes}</h2>
        <form onSubmit={(event) => { event.preventDefault(); const v = values(event); void command("/notes", {
          assignment_id: v.assignment, session_id: v.session || null, visibility: v.visibility, body: v.body,
        }); }}><AssignmentSelect items={activeAssignments} locale={locale} /><label>{f.session}<select name="session"><option value="">{f.general}</option>{data.sessions.map((item) => <option key={item.id} value={item.id}>{item.topic}</option>)}</select></label>
          <label>{f.visibility}<select name="visibility"><option value="mentor_private">{text.privateNote}</option><option value="shared_with_participant">{text.sharedNote}</option></select></label>
          <label>{f.note}<Textarea name="body" minLength={1} required /></label><Button disabled={busy} type="submit">{text.submit}</Button></form></Card>
      <Card className="program-panel"><h2>{text.goals}</h2>
        <form onSubmit={(event) => { event.preventDefault(); const v = values(event); void command("/goals", {
          assignment_id: v.assignment, title: v.title, description: v.description || null, target_date: v.target_date || null,
        }); }}><AssignmentSelect items={activeAssignments} locale={locale} /><label>{f.goal}<Input name="title" required /></label><label>{f.description}<Textarea name="description" /></label>
          <label>{f.targetDate}<Input name="target_date" type="date" /></label><Button disabled={busy} type="submit">{text.submit}</Button></form></Card>
      <Card className="program-panel"><h2>{text.actions}</h2>
        <form onSubmit={(event) => { event.preventDefault(); const v = values(event); void command("/action-items", {
          assignment_id: v.assignment, goal_id: v.goal || null, title: v.title, due_at: v.due_at ? iso(v.due_at) : null,
        }); }}><AssignmentSelect items={activeAssignments} locale={locale} /><label>{f.goal}<select name="goal"><option value="">{f.none}</option>{data.goals.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>
          <label>{f.action}<Input name="title" required /></label><label>{f.due}<Input name="due_at" type="datetime-local" /></label><Button disabled={busy} type="submit">{text.submit}</Button></form></Card>
      <Card className="program-panel"><h2>{text.followUps}</h2>
        <form onSubmit={(event) => { event.preventDefault(); const v = values(event); void command("/follow-ups", {
          assignment_id: v.assignment, session_id: v.session || null, purpose: v.purpose, due_at: iso(v.due_at),
        }); }}><AssignmentSelect items={activeAssignments} locale={locale} /><label>{f.session}<select name="session"><option value="">{f.general}</option>{data.sessions.map((item) => <option key={item.id} value={item.id}>{item.topic}</option>)}</select></label>
          <label>{f.purpose}<Input name="purpose" required /></label><label>{f.due}<Input name="due_at" type="datetime-local" required /></label><Button disabled={busy} type="submit">{text.submit}</Button></form></Card>
    </div></div>

    <div id="mentor-activity" className="mentor-group"><h2>{locale === "ta" ? "நடப்பு பதிவுகள்" : "Current records"}</h2>
    <Card className="program-panel"><h2>{text.assignments}</h2>{data.assignments.length === 0 && !busy && message !== text.error && <p className="mentor-empty">{text.empty}</p>}<ul className="program-list">{data.assignments.map((item) => <li key={item.id}>
      <strong>{item.participant_name}</strong><span>{item.mentor_name}</span><span className={`program-state program-state-${item.state}`}>{item.state}</span>
      {canAdmin && item.state === "active" && <Button disabled={busy} onClick={() => void command(`/assignments/${item.id}/end`, { expected_version: item.version, reason: "Mentoring assignment concluded" })}>{text.end}</Button>}
    </li>)}</ul></Card>
    <Card className="program-panel"><h2>{text.sessions}</h2>{data.sessions.length === 0 && !busy && message !== text.error && <p className="mentor-empty">{text.empty}</p>}<ul className="program-list">{data.sessions.map((item) => <li key={item.id}>
      <strong>{item.topic}</strong><span>{new Date(item.starts_at).toLocaleString(locale)}</span><span>{item.status}</span>
      {item.status === "scheduled" && <div><Button disabled={busy} onClick={() => void command(`/sessions/${item.id}/state`, { expected_version: item.version, target: "completed", reason: "Session outcomes recorded" })}>{text.complete}</Button>
        <Button disabled={busy} onClick={() => void command(`/sessions/${item.id}/state`, { expected_version: item.version, target: "cancelled", reason: "Session cancelled by mentor" })}>{text.cancel}</Button></div>}
    </li>)}</ul></Card>
    <Card className="program-panel"><h2>{text.goals}</h2>{data.goals.length === 0 && !busy && message !== text.error && <p className="mentor-empty">{text.empty}</p>}<ul className="program-list">{data.goals.map((item) => <li key={item.id}><strong>{item.title}</strong><span>{item.progress_percent}%</span><span>{item.state}</span></li>)}</ul></Card>
    <Card className="program-panel"><h2>{text.actions}</h2>{data.action_items.length === 0 && !busy && message !== text.error && <p className="mentor-empty">{text.empty}</p>}<ul className="program-list">{data.action_items.map((item) => <li key={item.id}><strong>{item.title}</strong><span>{item.state}</span>{item.state === "open" && <Button disabled={busy} onClick={() => void command(`/action-items/${item.id}/state`, { expected_version: item.version, target: "completed", reason: "Action reviewed as complete" })}>{text.complete}</Button>}</li>)}</ul></Card>
    <Card className="program-panel"><h2>{text.followUps}</h2>{data.follow_ups.length === 0 && !busy && message !== text.error && <p className="mentor-empty">{text.empty}</p>}<ul className="program-list">{data.follow_ups.map((item) => <li key={item.id}><strong>{item.purpose}</strong><span>{new Date(item.due_at).toLocaleString(locale)}</span>{item.overdue && <span role="alert">{text.overdue}</span>}{item.state === "scheduled" && <Button disabled={busy} onClick={() => void command(`/follow-ups/${item.id}/state`, { expected_version: item.version, target: "completed", reason: "Follow-up completed" })}>{text.complete}</Button>}</li>)}</ul>
      <p>{text.feedback}: {data.feedback_count}{data.average_rating !== null ? ` · ${data.average_rating}/5` : ""}</p></Card></div>
  </section>;
}

function ProfileSelect({ profiles, locale }: { profiles: Workspace["profiles"]; locale: Locale }) {
  const f = fields[locale];
  return <label>{f.mentor}<select name="profile" required><option value="">{f.select}</option>{profiles.filter((item) => item.state === "active").map((item) => <option key={item.id} value={item.id}>{item.display_name}</option>)}</select></label>;
}
function AssignmentSelect({ items, locale }: { items: Workspace["assignments"]; locale: Locale }) {
  const f = fields[locale];
  return <label>{f.participant}<select name="assignment" required><option value="">{f.select}</option>{items.map((item) => <option key={item.id} value={item.id}>{item.participant_name} · {item.mentor_name}</option>)}</select></label>;
}
