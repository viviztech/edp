"use client";

import { useEffect, useState } from "react";

type Locale = "en" | "ta";
type Code = typeof sections[number][0];
type Plan = {
  id: string; enrollment_id: string; status: string; version: number;
  completed_sections: number; total_sections: number;
  sections: Partial<Record<Code, string>>;
  revisions: { id: string; version: number; section_code: Code; body: string; created_at: string }[];
  submissions: { id: string; number: number; snapshot: Partial<Record<Code, string>>; created_at: string;
    review: { decision: string; reason: string; comments: Partial<Record<Code, string>> } | null }[];
};
type Entry = { enrollment_id: string; program_id: string; plan: Plan | null };

export const sections = [
  ["executive_summary", "Executive summary", "செயல் சுருக்கம்"],
  ["problem", "Problem", "பிரச்சினை"],
  ["solution", "Solution", "தீர்வு"],
  ["product_service", "Product or service", "தயாரிப்பு அல்லது சேவை"],
  ["customer_segments", "Customer segments", "வாடிக்கையாளர் பிரிவுகள்"],
  ["market", "Market", "சந்தை"],
  ["competition", "Competition", "போட்டி"],
  ["value_proposition", "Value proposition", "மதிப்பு முன்மொழிவு"],
  ["business_model", "Business model", "வணிக மாதிரி"],
  ["pricing", "Pricing", "விலை நிர்ணயம்"],
  ["sales_marketing", "Sales and marketing", "விற்பனை மற்றும் சந்தைப்படுத்தல்"],
  ["operations", "Operations", "செயல்பாடுகள்"],
  ["team", "Team", "குழு"],
  ["investment", "Investment", "முதலீடு"],
  ["revenue_assumptions", "Revenue assumptions", "வருவாய் அனுமானங்கள்"],
  ["expense_assumptions", "Expense assumptions", "செலவு அனுமானங்கள்"],
  ["break_even_inputs", "Break-even inputs", "சமநிலை கணக்கீட்டு உள்ளீடுகள்"],
  ["funding_requirement", "Funding requirement", "நிதித் தேவை"],
  ["risks", "Risks", "அபாயங்கள்"],
  ["milestones", "Milestones", "மைல்கற்கள்"],
] as const;

const labels = {
  en: { title: "My business plan", intro: "Build your plan section by section. Changes save automatically.",
    loading: "Loading your plans...", empty: "No active enrollment is available.", create: "Start a plan",
    saving: "Saving...", saved: "Saved", error: "Could not save. Your text is still here; retry when ready.",
    retry: "Retry save", history: "Recent revisions", section: "Section", completed: "sections completed",
    submit: "Submit for mentor review", submitted: "Submitted for review", approved: "Approved",
    changes: "Changes requested", incomplete: "Complete all sections before submitting.",
    feedback: "Mentor feedback", version: "Submitted version",
    caution: "Financial figures are your planning assumptions, not guaranteed outcomes." },
  ta: { title: "எனது வணிகத் திட்டம்", intro: "உங்கள் திட்டத்தைப் பிரிவு வாரியாக உருவாக்குங்கள். மாற்றங்கள் தானாகச் சேமிக்கப்படும்.",
    loading: "திட்டங்கள் ஏற்றப்படுகின்றன...", empty: "செயலில் உள்ள சேர்க்கை இல்லை.", create: "திட்டத்தைத் தொடங்கு",
    saving: "சேமிக்கப்படுகிறது...", saved: "சேமிக்கப்பட்டது", error: "சேமிக்க முடியவில்லை. உங்கள் உரை இங்கே உள்ளது; மீண்டும் முயற்சிக்கவும்.",
    retry: "மீண்டும் சேமி", history: "சமீபத்திய திருத்தங்கள்", section: "பிரிவு", completed: "பிரிவுகள் முடிந்தன",
    submit: "வழிகாட்டி மதிப்பாய்விற்கு சமர்ப்பி", submitted: "மதிப்பாய்விற்கு சமர்ப்பிக்கப்பட்டது", approved: "ஒப்புதல் அளிக்கப்பட்டது",
    changes: "மாற்றங்கள் கோரப்பட்டன", incomplete: "சமர்ப்பிக்கும் முன் எல்லா பிரிவுகளையும் நிரப்பவும்.",
    feedback: "வழிகாட்டியின் கருத்து", version: "சமர்ப்பிக்கப்பட்ட பதிப்பு",
    caution: "நிதி எண்கள் திட்டமிடல் அனுமானங்கள்; உறுதியான முடிவுகள் அல்ல." },
} as const;

async function post(url: string, body?: object): Promise<Response> {
  const csrf = await fetch("/api/session/csrf", { cache: "no-store" });
  if (!csrf.ok) throw new Error("csrf_failed");
  const { csrf_token } = await csrf.json() as { csrf_token: string };
  return fetch(url, { method: "POST", headers: { "Content-Type": "application/json", "x-csrf-token": csrf_token },
    body: JSON.stringify(body ?? {}) });
}

function Editor({ entry, org, locale }: { entry: Entry; org: string; locale: Locale }) {
  const text = labels[locale];
  const root = `/api/business-plans/organizations/${org}/enrollments/${entry.enrollment_id}`;
  const [plan, setPlan] = useState(entry.plan);
  const [drafts, setDrafts] = useState<Partial<Record<Code, string>>>(entry.plan?.sections ?? {});
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!plan || busy || failed || !["draft", "changes_requested"].includes(plan.status)) return;
    const dirty = sections.find(([code]) => (drafts[code] ?? "") !== (plan.sections[code] ?? ""));
    if (!dirty) return;
    const [code] = dirty;
    const body = drafts[code] ?? "";
    const timer = setTimeout(() => {
      setBusy(true); setMessage(text.saving);
      void (async () => {
        try {
          const response = await post(root + "/sections", { expected_version: plan.version, section_code: code, body });
          if (!response.ok) throw new Error("save_failed");
          setPlan(await response.json() as Plan); setMessage(text.saved);
        } catch { setFailed(true); setMessage(text.error); }
        finally { setBusy(false); }
      })();
    }, 900);
    return () => clearTimeout(timer);
  }, [plan, drafts, busy, failed, root, text]);

  async function createPlan() {
    setBusy(true); setMessage(text.saving);
    try {
      const response = await post(root);
      if (!response.ok) throw new Error("create_failed");
      setPlan(await response.json() as Plan); setMessage(text.saved);
    } catch { setMessage(text.error); }
    finally { setBusy(false); }
  }

  async function submitPlan() {
    if (!plan) return;
    setBusy(true); setMessage(text.saving);
    try {
      const response = await post(root + "/submit", { expected_version: plan.version });
      if (!response.ok) throw new Error("submit_failed");
      setPlan(await response.json() as Plan); setMessage(text.submitted);
    } catch { setMessage(text.error); }
    finally { setBusy(false); }
  }

  return <section className="program-panel">
    <h2>{text.title}</h2><p>{text.caution}</p>
    <p role="status">{message}</p>
    {!plan ? <button type="button" disabled={busy} onClick={() => void createPlan()}>{text.create}</button> : <>
      <p>{plan.completed_sections} / {plan.total_sections} {text.completed}</p>
      <div className="program-grid">{sections.map(([code, en, ta]) => <label key={code}>
        <strong>{locale === "ta" ? ta : en}</strong>
        <textarea value={drafts[code] ?? ""} maxLength={10000} rows={5}
          disabled={!(["draft", "changes_requested"].includes(plan.status))}
          onChange={(event) => setDrafts((current) => ({ ...current, [code]: event.target.value }))} />
      </label>)}</div>
      {failed && <button type="button" onClick={() => { setFailed(false); setMessage(""); }}>{text.retry}</button>}
      {["draft", "changes_requested"].includes(plan.status) && <>
        <p>{plan.completed_sections !== plan.total_sections ? text.incomplete : ""}</p>
        <button type="button" disabled={busy || failed || plan.completed_sections !== plan.total_sections ||
          sections.some(([code]) => (drafts[code] ?? "") !== (plan.sections[code] ?? ""))}
          onClick={() => void submitPlan()}>{text.submit}</button>
      </>}
      {plan.status === "submitted" && <p>{text.submitted}</p>}
      {plan.status === "approved" && <p>{text.approved}</p>}
      {plan.status === "changes_requested" && <p>{text.changes}</p>}
      {plan.submissions.map((submission) => <details key={submission.id}>
        <summary>{text.version} {submission.number} · {new Date(submission.created_at).toLocaleString(locale)}</summary>
        {submission.review && <section><h3>{text.feedback}: {submission.review.decision}</h3>
          <p>{submission.review.reason}</p>
          <ul>{Object.entries(submission.review.comments).map(([code, body]) =>
            <li key={code}><strong>{sections.find(([key]) => key === code)?.[locale === "ta" ? 2 : 1]}</strong>: {body}</li>)}</ul>
        </section>}
        <ul>{Object.entries(submission.snapshot).map(([code, body]) =>
          <li key={code}><strong>{sections.find(([key]) => key === code)?.[locale === "ta" ? 2 : 1]}</strong><p>{body}</p></li>)}</ul>
      </details>)}
      <details><summary>{text.history}</summary><ol className="program-list">
        {plan.revisions.map((revision) => <li key={revision.id}>
          <strong>{text.section}: {sections.find(([code]) => code === revision.section_code)?.[locale === "ta" ? 2 : 1]}</strong>
          <small> v{revision.version} · {new Date(revision.created_at).toLocaleString(locale)}</small>
          <p>{revision.body}</p>
        </li>)}
      </ol></details>
    </>}
  </section>;
}

export default function BusinessPlanView({ org, locale }: { org: string; locale: Locale }) {
  const text = labels[locale];
  const [entries, setEntries] = useState<Entry[]>([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState(false);
  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const response = await fetch(`/api/business-plans/organizations/${org}/mine`, { cache: "no-store" });
        if (!response.ok) throw new Error("load_failed");
        const data = await response.json() as { entries: Entry[] };
        if (active) setEntries(data.entries);
      } catch { if (active) setError(true); }
      finally { if (active) setBusy(false); }
    })();
    return () => { active = false; };
  }, [org]);
  return <><header className="program-heading"><div><p className="eyebrow">B01</p>
    <h1>{text.title}</h1><p>{text.intro}</p></div></header>
    {busy && <p role="status">{text.loading}</p>}
    {error && <p role="alert">{text.error}</p>}
    {!busy && !error && entries.length === 0 && <p>{text.empty}</p>}
    {entries.map((entry) => <Editor key={entry.enrollment_id} entry={entry} org={org} locale={locale} />)}
  </>;
}
