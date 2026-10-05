"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import type { components } from "../../../lib/api-contracts";
import { mentoringMessages } from "../../../lib/mentoring-messages";

type Locale = "en" | "ta";
type Mentoring = components["schemas"]["MyMentoring"];
const empty: Mentoring = { assignments: [], sessions: [], notes: [], goals: [], action_items: [], follow_ups: [], feedback: [] };

export default function MyMentoringView({ org, locale }: { org: string; locale: Locale }) {
  const text = mentoringMessages[locale];
  const root = `/api/mentoring/organizations/${org}`;
  const [data, setData] = useState<Mentoring>(empty);
  const [busy, setBusy] = useState(true);
  const [message, setMessage] = useState(text.loading as string);
  const load = useCallback(async () => {
    const response = await fetch(root + "/my-mentoring", { cache: "no-store" });
    if (!response.ok) throw new Error("request_failed");
    setData(await response.json() as Mentoring);
  }, [root]);
  useEffect(() => { let active = true; (async () => {
    try { await load(); if (active) setMessage(""); } catch { if (active) setMessage(text.error); }
    finally { if (active) setBusy(false); }
  })(); return () => { active = false; }; }, [load, text.error]);

  async function feedback(event: FormEvent<HTMLFormElement>, sessionId: string) {
    event.preventDefault(); setBusy(true);
    try {
      const values = Object.fromEntries(new FormData(event.currentTarget));
      const csrf = await fetch("/api/session/csrf", { cache: "no-store" });
      if (!csrf.ok) throw new Error("csrf_failed");
      const response = await fetch(root + "/feedback", { method: "POST", headers: {
        "Content-Type": "application/json", "x-csrf-token": (await csrf.json() as { csrf_token: string }).csrf_token,
      }, body: JSON.stringify({ session_id: sessionId, rating: Number(values.rating), comment: values.comment || null }) });
      if (!response.ok) throw new Error("request_failed");
      await load(); setMessage(text.saved);
    } catch { setMessage(text.error); } finally { setBusy(false); }
  }
  const reviewed = new Set(data.feedback.map((item) => item.session_id));
  return <>
    <header className="program-heading"><div><p className="eyebrow">{text.eyebrow}</p><h1>{text.learnerTitle}</h1><p>{text.learnerIntro}</p></div></header>
    <p role="status">{busy ? text.loading : message}</p>
    {!busy && data.assignments.length === 0 && <p>{text.empty}</p>}
    <div className="program-grid">{data.assignments.map((item) => <section className="program-panel" key={item.id}>
      <p className="eyebrow">{text.assignments}</p><h2>{item.mentor_name}</h2><p>{item.participant_name}</p>
      <span className={`program-state program-state-${item.state}`}>{item.state}</span>
    </section>)}</div>
    <section className="program-panel"><h2>{text.sessions}</h2><ul className="program-list">{data.sessions.map((item) => <li key={item.id}>
      <strong>{item.topic}</strong><span>{new Date(item.starts_at).toLocaleString(locale)}</span><span>{item.status}</span>
      {item.status === "completed" && !reviewed.has(item.id) && <form onSubmit={(event) => void feedback(event, item.id)}>
        <label>{text.rating}<select name="rating" defaultValue="5">{[5, 4, 3, 2, 1].map((rating) => <option key={rating}>{rating}</option>)}</select></label>
        <label>{text.feedback}<textarea name="comment" maxLength={2000} /></label><button disabled={busy}>{text.submit}</button>
      </form>}
    </li>)}</ul></section>
    <div className="program-grid">
      <section className="program-panel"><h2>{text.sharedNote}</h2><ul className="program-list">{data.notes.map((item) => <li key={item.id}><p>{item.body}</p><small>{new Date(item.created_at).toLocaleString(locale)}</small></li>)}</ul></section>
      <section className="program-panel"><h2>{text.goals}</h2><ul className="program-list">{data.goals.map((item) => <li key={item.id}><strong>{item.title}</strong><span>{item.progress_percent}% · {item.state}</span><p>{item.description}</p></li>)}</ul></section>
      <section className="program-panel"><h2>{text.actions}</h2><ul className="program-list">{data.action_items.map((item) => <li key={item.id}><strong>{item.title}</strong><span>{item.state}</span>{item.due_at && <small>{new Date(item.due_at).toLocaleString(locale)}</small>}</li>)}</ul></section>
      <section className="program-panel"><h2>{text.followUps}</h2><ul className="program-list">{data.follow_ups.map((item) => <li key={item.id}><strong>{item.purpose}</strong><span>{new Date(item.due_at).toLocaleString(locale)}</span>{item.overdue && <span role="alert">{text.overdue}</span>}</li>)}</ul></section>
    </div>
  </>;
}
