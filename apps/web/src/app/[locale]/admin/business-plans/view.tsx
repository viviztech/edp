"use client";

import { FormEvent, useEffect, useState } from "react";
import type { components } from "../../../../lib/api-contracts";
import { normalized } from "../../business-plan/editor-state";
import { sections } from "../../business-plan/view";

type Locale = "en" | "ta";
type Submission = components["schemas"]["SubmissionView"];
type Review = components["schemas"]["ReviewView"];
type ReviewCommand = components["schemas"]["ReviewPlan"];
type Draft = Pick<ReviewCommand, "decision" | "reason"> & { comments: Record<string, string> };
const emptyDraft = (): Draft => ({ decision: "changes_requested", reason: "", comments: {} });
const sectionLabel = (code: string, locale: Locale) =>
  sections.find(([key]) => key === code)?.[locale === "ta" ? 2 : 1] ?? code;

const text = {
  en: { loading: "Loading assigned plans...", empty: "No submitted plans are assigned to you.",
    error: "Could not load or save the review. Your entered feedback is still here.", saved: "Review saved.", version: "Submitted version",
    reason: "Review reason", comments: "Comments for this section", decision: "Decision",
    request: "Request changes", approve: "Approve", changes: "Changes requested", approved: "Approved", submit: "Record review", feedback: "Recorded feedback",
    latest: "Latest submission", earlier: "Earlier submission. Only the latest submission can be reviewed.",
    enrollment: "Enrollment", planVersion: "Last loaded plan version", snapshot: "Submitted content",
    conflict: "This plan changed or was already reviewed. Your entered feedback is still here. Refresh assigned plans before continuing.",
    refresh: "Refresh assigned plans", unavailable: "This submission is no longer available to review. Your entered feedback is still here.",
    retained: "Your unrecorded review", refreshFailed: "Review saved. The assigned list could not be refreshed; your recorded review is shown below.",
    paused: "Saving is paused. Refresh assigned plans before trying again.",
    reasonInvalid: "Enter a review reason with at least 3 non-space characters." },
  ta: { loading: "ஒதுக்கப்பட்ட திட்டங்கள் ஏற்றப்படுகின்றன...", empty: "உங்களுக்கு ஒதுக்கப்பட்ட திட்டங்கள் இல்லை.",
    error: "மதிப்பாய்வை ஏற்றவோ சேமிக்கவோ முடியவில்லை. உங்கள் கருத்துகள் இங்கே உள்ளன.", saved: "மதிப்பாய்வு சேமிக்கப்பட்டது.", version: "சமர்ப்பிக்கப்பட்ட பதிப்பு",
    reason: "மதிப்பாய்வு காரணம்", comments: "இந்தப் பிரிவுக்கான கருத்து", decision: "முடிவு",
    request: "மாற்றங்களை கோருங்கள்", approve: "ஒப்புதல் அளி", changes: "மாற்றங்கள் கோரப்பட்டன", approved: "ஒப்புதல் அளிக்கப்பட்டது", submit: "மதிப்பாய்வை பதிவு செய்", feedback: "பதிவான கருத்து",
    latest: "சமீபத்திய சமர்ப்பிப்பு", earlier: "முந்தைய சமர்ப்பிப்பு. சமீபத்திய சமர்ப்பிப்பை மட்டுமே மதிப்பாய்வு செய்யலாம்.",
    enrollment: "சேர்க்கை", planVersion: "கடைசியாக ஏற்றப்பட்ட திட்டப் பதிப்பு", snapshot: "சமர்ப்பிக்கப்பட்ட உள்ளடக்கம்",
    conflict: "இந்தத் திட்டம் மாறியுள்ளது அல்லது ஏற்கனவே மதிப்பாய்வு செய்யப்பட்டுள்ளது. உங்கள் கருத்துகள் இங்கே உள்ளன. தொடரும் முன் ஒதுக்கப்பட்ட திட்டங்களை மீண்டும் ஏற்றவும்.",
    refresh: "ஒதுக்கப்பட்ட திட்டங்களை மீண்டும் ஏற்று", unavailable: "இந்த சமர்ப்பிப்பை இனி மதிப்பாய்வு செய்ய முடியாது. உங்கள் கருத்துகள் இங்கே உள்ளன.",
    retained: "பதிவாகாத உங்கள் மதிப்பாய்வு", refreshFailed: "மதிப்பாய்வு சேமிக்கப்பட்டது. பட்டியலை மீண்டும் ஏற்ற முடியவில்லை; பதிவான மதிப்பாய்வு கீழே உள்ளது.",
    paused: "சேமிப்பு நிறுத்தப்பட்டுள்ளது. மீண்டும் முயலும் முன் ஒதுக்கப்பட்ட திட்டங்களை மீண்டும் ஏற்றவும்.",
    reasonInvalid: "குறைந்தது 3 எழுத்துகள் கொண்ட மதிப்பாய்வு காரணத்தை உள்ளிடவும்." },
} as const;

function matches(review: Review, command: ReviewCommand) {
  const comments = command.comments ?? {};
  return review.decision === command.decision && review.reason === normalized(command.reason) &&
    Object.keys(review.comments).length === Object.keys(comments).length &&
    Object.entries(comments).every(([code, body]) => review.comments[code] === normalized(body));
}

function commandFor(draft: Draft, version: number): ReviewCommand {
  return { expected_version: version, decision: draft.decision, reason: normalized(draft.reason),
    comments: Object.fromEntries(Object.entries(draft.comments).filter(([, body]) => normalized(body))
      .map(([code, body]) => [code, normalized(body)])),
  };
}

function ReviewCard({ item, org, locale, latest, available, onRefresh }: {
  item: Submission; org: string; locale: Locale; latest: boolean; available: boolean;
  onRefresh: () => Promise<Submission[]>;
}) {
  const labels = text[locale];
  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [busy, setBusy] = useState(false);
  const [paused, setPaused] = useState(false);
  const [message, setMessage] = useState("");
  const [recorded, setRecorded] = useState<Review | null>(null);
  const [attempt, setAttempt] = useState<ReviewCommand | null>(null);
  const review = item.review ?? recorded;
  const hasDraft = !!draft.reason || Object.values(draft.comments).some(Boolean);
  const locked = !available || !latest || !!review;

  async function refresh(command: ReviewCommand | null = attempt) {
    setBusy(true);
    try {
      const items = await onRefresh();
      const current = items.find((candidate) => candidate.id === item.id);
      if (!current) {
        setPaused(true); setMessage(labels.unavailable);
      } else {
        if (current.review) {
          setRecorded(current.review);
          if (command && matches(current.review, command)) {
            if (matches(current.review, commandFor(draft, item.plan_version))) setDraft(emptyDraft());
            setAttempt(null); setMessage(labels.saved);
          } else setMessage("");
        } else setMessage("");
        setPaused(false);
      }
    } catch {
      setPaused(true); setMessage(labels.error);
    } finally { setBusy(false); }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || paused || locked) return;
    if (normalized(draft.reason).length < 3) { setMessage(labels.reasonInvalid); return; }
    const command = commandFor(draft, item.plan_version);
    setBusy(true); setMessage(""); setAttempt(command);
    let committed = false;
    try {
      const csrf = await fetch("/api/session/csrf", { cache: "no-store" });
      if (!csrf.ok) throw new Error("csrf_failed");
      const { csrf_token } = await csrf.json() as { csrf_token: string };
      const response = await fetch(`/api/business-plans/organizations/${org}/submissions/${item.id}/review`, {
        method: "POST", headers: { "Content-Type": "application/json", "x-csrf-token": csrf_token },
        body: JSON.stringify(command),
      });
      if (!response.ok) {
        setPaused(true); setMessage(response.status === 409 ? labels.conflict : labels.error);
        return;
      }
      const result = await response.json() as Review;
      committed = true;
      setRecorded(result); setDraft(emptyDraft()); setAttempt(null); setMessage(labels.saved);
      // The returned immutable review is already committed even if this list refresh fails.
      await onRefresh();
    } catch {
      if (committed) setMessage(labels.refreshFailed);
      else { setPaused(true); setMessage(labels.error); }
    } finally { setBusy(false); }
  }

  return <section className="program-panel">
    <h2>{labels.version} {item.number}</h2>
    <p>{labels.enrollment}: {item.enrollment_id}</p>
    <p>{labels.planVersion}: {item.plan_version}</p>
    <p>{latest ? labels.latest : labels.earlier}</p>
    <small>{new Date(item.created_at).toLocaleString(locale)}</small>
    <p role="status">{message}</p>
    {!available && <p role="alert">{labels.unavailable}</p>}
    {paused && <p>{labels.paused}</p>}
    {(paused || !available || (review && message === labels.refreshFailed)) &&
      <button type="button" disabled={busy} onClick={() => void refresh()}>{labels.refresh}</button>}
    <h3>{labels.snapshot}</h3>
    <ul className="program-list">{Object.entries(item.snapshot).map(([code, body]) =>
      <li key={code}><strong>{sectionLabel(code, locale)}</strong><p style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{body}</p></li>)}</ul>
    {review && <section><h3>{labels.feedback}: {review.decision === "approved" ? labels.approved : labels.changes}</h3>
      <p>{review.reason}</p><ul>{Object.entries(review.comments).map(([code, body]) =>
        <li key={code}><strong>{sectionLabel(code, locale)}</strong>: {body}</li>)}</ul></section>}
    {(!locked || hasDraft) && <form onSubmit={(event) => void submit(event)}>
      {locked && hasDraft && <h3>{labels.retained}</h3>}
      <fieldset disabled={busy || locked}>
        <label>{labels.decision}<select name="decision" value={draft.decision}
          onChange={(event) => setDraft({ ...draft, decision: event.target.value as Draft["decision"] })}>
          <option value="changes_requested">{labels.request}</option>
          <option value="approved">{labels.approve}</option>
        </select></label>
        <label>{labels.reason}<textarea name="reason" required minLength={3} maxLength={500}
          value={draft.reason} onChange={(event) => setDraft({ ...draft, reason: event.target.value })} /></label>
        <details><summary>{labels.comments}</summary>
          {Object.keys(item.snapshot).map((code) => <label key={code}>
            {sectionLabel(code, locale)}<textarea name={`comment:${code}`} maxLength={2000}
              value={draft.comments[code] ?? ""} onChange={(event) => setDraft({ ...draft, comments: { ...draft.comments, [code]: event.target.value } })} />
          </label>)}
        </details>
        <button disabled={paused || busy || locked}>{labels.submit}</button>
      </fieldset>
    </form>}
  </section>;
}

function ReviewList({ org, locale }: { org: string; locale: Locale }) {
  const labels = text[locale];
  const [items, setItems] = useState<Submission[]>([]);
  const [available, setAvailable] = useState<string[]>([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState(false);
  async function load() {
    const response = await fetch(`/api/business-plans/organizations/${org}/assigned`, { cache: "no-store" });
    if (!response.ok) throw new Error("load_failed");
    const data = await response.json() as components["schemas"]["MentorPlans"];
    const ids = data.submissions.map((item) => item.id);
    // Keep already-visible drafts when assignment or access changes during a refresh.
    setItems((previous) => [...data.submissions, ...previous.filter((item) => !ids.includes(item.id))]);
    setAvailable(ids); setError(false);
    return data.submissions;
  }
  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const response = await fetch(`/api/business-plans/organizations/${org}/assigned`, { cache: "no-store" });
        if (!response.ok) throw new Error("load_failed");
        const data = await response.json() as components["schemas"]["MentorPlans"];
        if (active) { setItems(data.submissions); setAvailable(data.submissions.map((item) => item.id)); }
      } catch { if (active) setError(true); }
      finally { if (active) setBusy(false); }
    })();
    return () => { active = false; };
  }, [org]);
  const latest = new Map<string, number>();
  for (const item of items) latest.set(item.enrollment_id, Math.max(latest.get(item.enrollment_id) ?? 0, item.number));
  return <>
    {busy && <p role="status">{labels.loading}</p>}
    {error && <><p role="alert">{labels.error}</p><button type="button" onClick={() => {
      setBusy(true); void load().catch(() => setError(true)).finally(() => setBusy(false));
    }}>{labels.refresh}</button></>}
    {!busy && !error && items.length === 0 && <p>{labels.empty}</p>}
    {items.map((item) => <ReviewCard key={item.id} item={item} org={org} locale={locale}
      latest={latest.get(item.enrollment_id) === item.number} available={available.includes(item.id)} onRefresh={load} />)}
  </>;
}

export default function MentorPlanReviews({ org, locale }: { org: string; locale: Locale }) {
  return <ReviewList key={org} org={org} locale={locale} />;
}
