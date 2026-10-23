"use client";

import { useCallback, useEffect, useReducer, useState } from "react";
import type { components } from "../../../lib/api-contracts";
import { dirtyCodes, editable, editorReducer, initialState, type Entry, type Plan } from "./editor-state";

type Locale = "en" | "ta";

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

const recoveryLabels = {
  en: { refreshing: "Checking the latest saved plan. Your edits are still here.",
    unsavedChanges: "Unsaved changes",
    recovered: "Latest saved version loaded. Your remaining edits will save automatically.",
    failed: "Could not refresh the saved plan or confirm your access. Your edits are still here. Saving is paused.",
    saveFailed: "These edits could not be saved. Check the text size and content, then refresh the saved plan to retry. Your edits are still here; saving is paused.",
    refresh: "Refresh saved plan", conflict: "Review conflicting edits",
    explanation: "This plan changed elsewhere. Compare the saved version with your edits before continuing. Saving is paused.",
    savedVersion: "Saved version", localVersion: "Your edits", keep: "Keep my edits", load: "Load saved version",
    discard: "Discard all unsaved edits and load the saved version?", unsaved: "You have unsaved business-plan edits. Leave this page and lose them?",
    locked: "This plan is now submitted or approved. Your unsaved edits are preserved below, but cannot be saved while the plan is locked." },
  ta: { refreshing: "சேமிக்கப்பட்ட சமீபத்திய திட்டம் சரிபார்க்கப்படுகிறது. உங்கள் திருத்தங்கள் இங்கே உள்ளன.",
    unsavedChanges: "சேமிக்காத திருத்தங்கள்",
    recovered: "சேமிக்கப்பட்ட சமீபத்திய பதிப்பு ஏற்றப்பட்டது. மீதமுள்ள உங்கள் திருத்தங்கள் தானாகச் சேமிக்கப்படும்.",
    failed: "சேமித்த திட்டத்தையோ உங்கள் அணுகலையோ உறுதிப்படுத்த முடியவில்லை. உங்கள் திருத்தங்கள் இங்கே உள்ளன. சேமிப்பு நிறுத்தப்பட்டுள்ளது.",
    saveFailed: "இந்தத் திருத்தங்களைச் சேமிக்க முடியவில்லை. உரையின் அளவையும் உள்ளடக்கத்தையும் சரிபார்த்து, மீண்டும் முயற்சிக்க சேமித்த திட்டத்தை ஏற்றவும். உங்கள் திருத்தங்கள் இங்கே உள்ளன; சேமிப்பு நிறுத்தப்பட்டுள்ளது.",
    refresh: "சேமித்த திட்டத்தை மீண்டும் ஏற்று", conflict: "முரண்படும் திருத்தங்களைப் பரிசீலிக்கவும்",
    explanation: "இந்தத் திட்டம் வேறொரு இடத்தில் மாற்றப்பட்டுள்ளது. தொடர்வதற்கு முன் சேமித்த பதிப்பையும் உங்கள் திருத்தங்களையும் ஒப்பிடவும். சேமிப்பு நிறுத்தப்பட்டுள்ளது.",
    savedVersion: "சேமித்த பதிப்பு", localVersion: "உங்கள் திருத்தங்கள்", keep: "என் திருத்தங்களை வைத்திரு", load: "சேமித்த பதிப்பை ஏற்று",
    discard: "சேமிக்காத எல்லா திருத்தங்களையும் கைவிட்டு சேமித்த பதிப்பை ஏற்றவா?", unsaved: "வணிகத் திட்டத்தில் சேமிக்காத திருத்தங்கள் உள்ளன. அவற்றை இழந்து இந்தப் பக்கத்தை விட்டு வெளியேறவா?",
    locked: "இந்தத் திட்டம் இப்போது சமர்ப்பிக்கப்பட்டது அல்லது ஒப்புதல் பெற்றது. சேமிக்காத உங்கள் திருத்தங்கள் கீழே பாதுகாக்கப்பட்டுள்ளன; திட்டம் பூட்டப்பட்டுள்ளபோது சேமிக்க முடியாது." },
} as const;

function useUnsavedNavigation(unsaved: boolean, message: string) {
  useEffect(() => {
    if (!unsaved) return;
    const beforeUnload = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    const followLink = (event: MouseEvent) => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.altKey || event.shiftKey) return;
      const link = event.target instanceof Element ? event.target.closest("a[href]") : null;
      if (!(link instanceof HTMLAnchorElement) || link.hasAttribute("download") || (link.target && link.target !== "_self")) return;
      const destination = new URL(link.href, window.location.href);
      const current = new URL(window.location.href);
      if (destination.origin === current.origin && destination.pathname === current.pathname && destination.search === current.search) return;
      if (!window.confirm(message)) { event.preventDefault(); event.stopPropagation(); }
    };
    window.addEventListener("beforeunload", beforeUnload);
    document.addEventListener("click", followLink, true);
    return () => {
      window.removeEventListener("beforeunload", beforeUnload);
      document.removeEventListener("click", followLink, true);
    };
  }, [unsaved, message]);
}

function Editor({ entry, org, locale, onUnsavedChange }: {
  entry: Entry; org: string; locale: Locale; onUnsavedChange: (id: string, unsaved: boolean) => void;
}) {
  const text = labels[locale];
  const recovery = recoveryLabels[locale];
  const root = `/api/business-plans/organizations/${org}/enrollments/${entry.enrollment_id}`;
  const [state, dispatch] = useReducer(editorReducer, entry.plan, initialState);
  const { plan, drafts, phase } = state;
  const dirty = dirtyCodes(state);
  const unsaved = dirty.length > 0 || state.attempt !== null;
  const busy = ["saving", "creating", "submitting", "refreshing"].includes(phase);
  const comparison = phase === "conflict" ? state.conflicts : phase === "locked" ? dirty : [];
  const message = phase === "locked" && state.notice === "recovered" ? "" : state.notice === "saved" && unsaved ? recovery.unsavedChanges :
    state.notice === "recovered" ? recovery.recovered : state.notice === "refreshing" ? recovery.refreshing :
    state.notice ? text[state.notice] : "";
  useEffect(() => {
    onUnsavedChange(entry.enrollment_id, unsaved);
    return () => onUnsavedChange(entry.enrollment_id, false);
  }, [entry.enrollment_id, onUnsavedChange, unsaved]);

  const refreshSaved = useCallback(async (requirePlan: boolean, pauseOnDirty = false, uncertain?: boolean) => {
    dispatch({ type: "refresh", pauseOnDirty, uncertain });
    try {
      const response = await fetch(`/api/business-plans/organizations/${org}/mine`, { cache: "no-store" });
      if (!response.ok) throw new Error("refresh_failed");
      const data = await response.json() as components["schemas"]["MyPlans"];
      const refreshed = data.entries.find((candidate) => candidate.enrollment_id === entry.enrollment_id);
      if (!refreshed || (requirePlan && !refreshed.plan)) throw new Error("access_changed");
      dispatch({ type: "refreshed", plan: refreshed.plan });
    } catch { dispatch({ type: "refresh_failed" }); }
  }, [org, entry.enrollment_id]);

  useEffect(() => {
    if (!plan || phase !== "ready" || !editable(plan)) return;
    const changed = dirtyCodes(state);
    const code = sections.find(([section]) => changed.includes(section))?.[0];
    if (!code) return;
    const body = drafts[code] ?? "";
    const timer = setTimeout(() => {
      dispatch({ type: "save", attempt: { code, body, version: plan.version } });
      void (async () => {
        let pauseOnDirty = true;
        let uncertain = true;
        try {
          const payload: components["schemas"]["SaveSection"] = { expected_version: plan.version, section_code: code, body };
          const response = await post(root + "/sections", payload);
          if (!response.ok) {
            pauseOnDirty = response.status !== 409;
            uncertain = response.status >= 500;
            throw new Error("save_failed");
          }
          dispatch({ type: "saved", plan: await response.json() as Plan });
        } catch { await refreshSaved(true, pauseOnDirty, uncertain); }
      })();
    }, 900);
    return () => clearTimeout(timer);
  }, [state, plan, drafts, phase, root, refreshSaved]);

  async function createPlan() {
    if (phase !== "ready") return;
    dispatch({ type: "start", phase: "creating" });
    try {
      const response = await post(root);
      if (!response.ok) throw new Error("create_failed");
      dispatch({ type: "saved", plan: await response.json() as Plan });
    } catch { await refreshSaved(false); }
  }

  async function submitPlan() {
    if (!plan || !editable(plan) || phase !== "ready" || unsaved || plan.completed_sections !== plan.total_sections) return;
    dispatch({ type: "start", phase: "submitting" });
    try {
      const payload: components["schemas"]["SubmitPlan"] = { expected_version: plan.version };
      const response = await post(root + "/submit", payload);
      if (!response.ok) throw new Error("submit_failed");
      dispatch({ type: "saved", plan: await response.json() as Plan });
    } catch { await refreshSaved(true); }
  }

  return <section className="program-panel">
    <h2>{text.title}</h2><p>{text.caution}</p>
    <p role="status">{message}</p>
    {["refresh_failed", "save_failed"].includes(phase) && <div role="alert"><p>{phase === "save_failed" ? recovery.saveFailed : recovery.failed}</p>
      <button type="button" onClick={() => void refreshSaved(!!plan)}>{recovery.refresh}</button></div>}
    {phase === "locked" && unsaved && <p role="alert">{recovery.locked}</p>}
    {!plan ? <button type="button" disabled={phase !== "ready"} onClick={() => void createPlan()}>{text.create}</button> : <>
      <p>{plan.completed_sections} / {plan.total_sections} {text.completed}</p>
      <div className="program-grid">{sections.map(([code, en, ta]) => <label key={code}>
        <strong>{locale === "ta" ? ta : en}</strong>
        <textarea value={drafts[code] ?? ""} maxLength={10000} rows={5}
          readOnly={!editable(plan) || phase === "submitting"}
          onChange={(event) => {
            if (editable(plan) && phase !== "submitting") dispatch({ type: "edit", code, body: event.target.value });
          }} />
      </label>)}</div>
      {comparison.length > 0 && <section aria-label={recovery.conflict}>
        <h3>{recovery.conflict}</h3>
        {phase === "conflict" && <p role="alert">{recovery.explanation}</p>}
        {comparison.map((code) => <article key={code}>
          <h4>{sections.find(([section]) => section === code)?.[locale === "ta" ? 2 : 1]}</h4>
          <p><strong>{recovery.savedVersion}</strong></p><pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{plan.sections[code] ?? ""}</pre>
          <p><strong>{recovery.localVersion}</strong></p><pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{drafts[code] ?? ""}</pre>
        </article>)}
        {phase === "conflict" && <button type="button" onClick={() => dispatch({ type: "keep" })}>{recovery.keep}</button>}
        <button type="button" onClick={() => {
          if (window.confirm(recovery.discard)) dispatch({ type: "discard" });
        }}>{recovery.load}</button>
      </section>}
      {editable(plan) && <>
        <p>{plan.completed_sections !== plan.total_sections ? text.incomplete : ""}</p>
        <button type="button" disabled={busy || phase !== "ready" || unsaved || plan.completed_sections !== plan.total_sections}
          onClick={() => void submitPlan()}>{text.submit}</button>
      </>}
      {plan.status === "submitted" && <p>{text.submitted}</p>}
      {plan.status === "approved" && <p>{text.approved}</p>}
      {plan.status === "changes_requested" && <p>{text.changes}</p>}
      {plan.submissions.map((submission) => <details key={submission.id}>
        <summary>{text.version} {submission.number} · {new Date(submission.created_at).toLocaleString(locale)}</summary>
        {submission.review && <section><h3>{text.feedback}: {submission.review.decision === "approved" ? text.approved : text.changes}</h3>
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
  const [unsavedPlans, setUnsavedPlans] = useState<Record<string, boolean>>({});
  const onUnsavedChange = useCallback((id: string, unsaved: boolean) => {
    setUnsavedPlans((current) => current[id] === unsaved ? current : { ...current, [id]: unsaved });
  }, []);
  useUnsavedNavigation(Object.values(unsavedPlans).some(Boolean), recoveryLabels[locale].unsaved);
  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const response = await fetch(`/api/business-plans/organizations/${org}/mine`, { cache: "no-store" });
        if (!response.ok) throw new Error("load_failed");
        const data = await response.json() as components["schemas"]["MyPlans"];
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
    {entries.map((entry) => <Editor key={entry.enrollment_id} entry={entry} org={org} locale={locale} onUnsavedChange={onUnsavedChange} />)}
  </>;
}
