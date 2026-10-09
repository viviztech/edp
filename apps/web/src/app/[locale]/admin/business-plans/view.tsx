"use client";

import { FormEvent, useEffect, useState } from "react";
import { sections } from "../../business-plan/view";

type Locale = "en" | "ta";
type Submission = {
  id: string; enrollment_id: string; plan_version: number; number: number;
  snapshot: Record<string, string>; created_at: string;
  review: { decision: string; reason: string; comments: Record<string, string> } | null;
};

const sectionLabel = (code: string, locale: Locale) =>
  sections.find(([key]) => key === code)?.[locale === "ta" ? 2 : 1] ?? code;

const text = {
  en: { loading: "Loading assigned plans...", empty: "No submitted plans are assigned to you.",
    error: "Could not load or save the review.", saved: "Review saved.", version: "Version",
    reason: "Review reason", comments: "Comments for this section", decision: "Decision",
    request: "Request changes", approve: "Approve", submit: "Record review", feedback: "Recorded feedback" },
  ta: { loading: "ஒதுக்கப்பட்ட திட்டங்கள் ஏற்றப்படுகின்றன...", empty: "உங்களுக்கு ஒதுக்கப்பட்ட திட்டங்கள் இல்லை.",
    error: "மதிப்பாய்வை ஏற்றவோ சேமிக்கவோ முடியவில்லை.", saved: "மதிப்பாய்வு சேமிக்கப்பட்டது.", version: "பதிப்பு",
    reason: "மதிப்பாய்வு காரணம்", comments: "இந்தப் பிரிவுக்கான கருத்து", decision: "முடிவு",
    request: "மாற்றங்களை கோருங்கள்", approve: "ஒப்புதல் அளி", submit: "மதிப்பாய்வை பதிவு செய்", feedback: "பதிவான கருத்து" },
} as const;

function ReviewCard({ item, org, locale, onSaved }: {
  item: Submission; org: string; locale: Locale; onSaved: () => Promise<void>;
}) {
  const labels = text[locale];
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setMessage("");
    try {
      const values = new FormData(event.currentTarget);
      const comments: Record<string, string> = {};
      for (const [key, value] of values.entries()) {
        if (key.startsWith("comment:") && typeof value === "string" && value.trim()) {
          comments[key.slice(8)] = value.trim();
        }
      }
      const csrf = await fetch("/api/session/csrf", { cache: "no-store" });
      if (!csrf.ok) throw new Error("csrf_failed");
      const { csrf_token } = await csrf.json() as { csrf_token: string };
      const response = await fetch(`/api/business-plans/organizations/${org}/submissions/${item.id}/review`, {
        method: "POST", headers: { "Content-Type": "application/json", "x-csrf-token": csrf_token },
        body: JSON.stringify({ expected_version: item.plan_version, decision: values.get("decision"),
          reason: values.get("reason"), comments }),
      });
      if (!response.ok) throw new Error("review_failed");
      await onSaved(); setMessage(labels.saved);
    } catch { setMessage(labels.error); }
    finally { setBusy(false); }
  }
  return <section className="program-panel">
    <h2>{labels.version} {item.number}</h2><small>{new Date(item.created_at).toLocaleString(locale)}</small>
    <p role="status">{message}</p>
    <ul className="program-list">{Object.entries(item.snapshot).map(([code, body]) =>
      <li key={code}><strong>{sectionLabel(code, locale)}</strong><p>{body}</p></li>)}</ul>
    {item.review ? <section><h3>{labels.feedback}: {item.review.decision}</h3>
      <p>{item.review.reason}</p><ul>{Object.entries(item.review.comments).map(([code, body]) =>
        <li key={code}><strong>{sectionLabel(code, locale)}</strong>: {body}</li>)}</ul></section>
      : <form onSubmit={(event) => void submit(event)}>
        <label>{labels.decision}<select name="decision" defaultValue="changes_requested">
          <option value="changes_requested">{labels.request}</option>
          <option value="approved">{labels.approve}</option>
        </select></label>
        <label>{labels.reason}<textarea name="reason" required minLength={3} maxLength={500} /></label>
        <details><summary>{labels.comments}</summary>
          {Object.keys(item.snapshot).map((code) => <label key={code}>
            {sectionLabel(code, locale)}<textarea name={`comment:${code}`} maxLength={2000} />
          </label>)}
        </details>
        <button disabled={busy}>{labels.submit}</button>
      </form>}
  </section>;
}

export default function MentorPlanReviews({ org, locale }: { org: string; locale: Locale }) {
  const labels = text[locale];
  const [items, setItems] = useState<Submission[]>([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState(false);
  async function load() {
    const response = await fetch(`/api/business-plans/organizations/${org}/assigned`, { cache: "no-store" });
    if (!response.ok) throw new Error("load_failed");
    setItems((await response.json() as { submissions: Submission[] }).submissions);
  }
  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const response = await fetch(`/api/business-plans/organizations/${org}/assigned`, { cache: "no-store" });
        if (!response.ok) throw new Error("load_failed");
        const data = await response.json() as { submissions: Submission[] };
        if (active) setItems(data.submissions);
      } catch { if (active) setError(true); }
      finally { if (active) setBusy(false); }
    })();
    return () => { active = false; };
  }, [org]);
  return <>
    {busy && <p role="status">{labels.loading}</p>}
    {error && <p role="alert">{labels.error}</p>}
    {!busy && !error && items.length === 0 && <p>{labels.empty}</p>}
    {items.map((item) => <ReviewCard key={item.id} item={item} org={org} locale={locale} onSaved={load} />)}
  </>;
}
