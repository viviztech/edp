"use client";

import { useCallback, useEffect, useState } from "react";
import type { components } from "../../../lib/api-contracts";

type Form = components["schemas"]["FormView"];
type Draft = components["schemas"]["DraftView"];
type Field = components["schemas"]["FieldView"];

const copy = {
  en: {
    eyebrow: "Applicant workspace", unavailable: "Applications are not open for this organization.",
    draftOnly: "Draft saving is available for development review. Submission and document collection remain disabled until the application and privacy policies are approved.",
    start: "Start draft", save: "Save draft", saving: "Saving...", saved: "Draft saved", error: "The draft could not be saved. Refresh and try again.",
    conflict: "This draft changed in another session. Refresh before continuing.", completion: "Required fields complete",
    version: "Draft version", empty: "This form has no configured fields.", yes: "Yes", no: "No",
  },
  ta: {
    eyebrow: "\u0bb5\u0bbf\u0ba3\u0bcd\u0ba3\u0baa\u0bcd\u0baa\u0ba4\u0bbe\u0bb0\u0bb0\u0bcd \u0baa\u0ba3\u0bbf\u0baf\u0bbf\u0b9f\u0bae\u0bcd",
    unavailable: "\u0b87\u0ba8\u0bcd\u0ba4 \u0ba8\u0bbf\u0bb1\u0bc1\u0bb5\u0ba9\u0ba4\u0bcd\u0ba4\u0bbf\u0bb1\u0bcd\u0b95\u0bc1 \u0bb5\u0bbf\u0ba3\u0bcd\u0ba3\u0baa\u0bcd\u0baa\u0b99\u0bcd\u0b95\u0bb3\u0bcd \u0ba4\u0bbf\u0bb1\u0b95\u0bcd\u0b95\u0baa\u0bcd\u0baa\u0b9f\u0bb5\u0bbf\u0bb2\u0bcd\u0bb2\u0bc8.",
    draftOnly: "\u0bae\u0bc7\u0bae\u0bcd\u0baa\u0bbe\u0b9f\u0bcd\u0b9f\u0bc1 \u0bae\u0ba4\u0bbf\u0baa\u0bcd\u0baa\u0bbe\u0baf\u0bcd\u0bb5\u0bbf\u0bb1\u0bcd\u0b95\u0bbe\u0b95 \u0bb5\u0bb0\u0bc8\u0bb5\u0bc8 \u0b9a\u0bc7\u0bae\u0bbf\u0b95\u0bcd\u0b95\u0bb2\u0bbe\u0bae\u0bcd. \u0b95\u0bca\u0bb3\u0bcd\u0b95\u0bc8 \u0b92\u0baa\u0bcd\u0baa\u0bc1\u0ba4\u0bb2\u0bcd \u0bb5\u0bb0\u0bc8 \u0b9a\u0bae\u0bb0\u0bcd\u0baa\u0bcd\u0baa\u0bbf\u0baa\u0bcd\u0baa\u0bc1 \u0bae\u0bc1\u0b9f\u0b95\u0bcd\u0b95\u0baa\u0bcd\u0baa\u0b9f\u0bcd\u0b9f\u0bc1\u0bb3\u0bcd\u0bb3\u0ba4\u0bc1.",
    start: "\u0bb5\u0bb0\u0bc8\u0bb5\u0bc8\u0ba4\u0bcd \u0ba4\u0bca\u0b9f\u0b99\u0bcd\u0b95\u0bc1", save: "\u0bb5\u0bb0\u0bc8\u0bb5\u0bc8 \u0b9a\u0bc7\u0bae\u0bbf", saving: "\u0b9a\u0bc7\u0bae\u0bbf\u0b95\u0bcd\u0b95\u0bbf\u0bb1\u0ba4\u0bc1...", saved: "\u0bb5\u0bb0\u0bc8\u0bb5\u0bc1 \u0b9a\u0bc7\u0bae\u0bbf\u0b95\u0bcd\u0b95\u0baa\u0bcd\u0baa\u0b9f\u0bcd\u0b9f\u0ba4\u0bc1",
    error: "\u0bb5\u0bb0\u0bc8\u0bb5\u0bc8 \u0b9a\u0bc7\u0bae\u0bbf\u0b95\u0bcd\u0b95 \u0bae\u0bc1\u0b9f\u0bbf\u0baf\u0bb5\u0bbf\u0bb2\u0bcd\u0bb2\u0bc8.", conflict: "\u0bb5\u0bb0\u0bc8\u0bb5\u0bc1 \u0bae\u0bbe\u0bb1\u0bbf\u0baf\u0bc1\u0bb3\u0bcd\u0bb3\u0ba4\u0bc1. \u0baa\u0bc1\u0ba4\u0bc1\u0baa\u0bcd\u0baa\u0bbf\u0b95\u0bcd\u0b95\u0bb5\u0bc1\u0bae\u0bcd.",
    completion: "\u0ba4\u0bc7\u0bb5\u0bc8\u0baf\u0bbe\u0ba9 \u0baa\u0bc1\u0bb2\u0b99\u0bcd\u0b95\u0bb3\u0bcd", version: "\u0bb5\u0bb0\u0bc8\u0bb5\u0bc1 \u0baa\u0ba4\u0bbf\u0baa\u0bcd\u0baa\u0bc1", empty: "\u0baa\u0bc1\u0bb2\u0b99\u0bcd\u0b95\u0bb3\u0bcd \u0b87\u0bb2\u0bcd\u0bb2\u0bc8.", yes: "\u0b86\u0bae\u0bcd", no: "\u0b87\u0bb2\u0bcd\u0bb2\u0bc8",
  },
} as const;

export default function ApplicationDraft({ locale, org }: { locale: "en" | "ta"; org: string }) {
  const t = copy[locale];
  const root = `/api/applications/organizations/${org}`;
  const [form, setForm] = useState<Form | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const mutate = useCallback(async <T,>(path: string, method: "POST" | "PATCH", body: unknown): Promise<T> => {
    const tokenResponse = await fetch("/api/session/csrf", { cache: "no-store" });
    if (!tokenResponse.ok) throw new Error("service");
    const csrf = (await tokenResponse.json()).csrf_token;
    const response = await fetch(path, {
      method, cache: "no-store",
      headers: { "Content-Type": "application/json", "x-csrf-token": csrf },
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error(response.status === 409 ? "conflict" : "request");
    return response.json();
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([
      fetch(`${root}/form`, { cache: "no-store" }),
      fetch(`${root}/draft`, { cache: "no-store" }),
    ]).then(async ([formResponse, draftResponse]) => {
      if (!formResponse.ok) throw new Error("unavailable");
      const loadedForm: Form = await formResponse.json();
      const loadedDraft: Draft | null = draftResponse.ok ? await draftResponse.json() : null;
      if (!active) return;
      setForm(loadedForm);
      setDraft(loadedDraft);
      if (loadedDraft) setValues(Object.fromEntries(loadedDraft.answers.map((item) => [item.field_id, item.value])));
    }).catch((error) => { if (active) setMessage(error instanceof Error && error.message === "unavailable" ? t.unavailable : t.error); });
    return () => { active = false; };
  }, [root, t.error, t.unavailable]);

  async function start() {
    setBusy(true); setMessage("");
    try {
      const created = await mutate<Draft>(`${root}/draft`, "POST", {});
      setDraft(created); setForm(created.form); setMessage(t.saved);
    } catch { setMessage(t.error); } finally { setBusy(false); }
  }
  async function save() {
    if (!draft) return;
    setBusy(true); setMessage("");
    try {
      const updated = await mutate<Draft>(`${root}/draft/${draft.id}`, "PATCH", {
        expected_version: draft.version,
        answers: Object.entries(values).map(([field_id, value]) => ({ field_id, value })),
      });
      setDraft(updated); setMessage(t.saved);
    } catch (error) {
      setMessage(error instanceof Error && error.message === "conflict" ? t.conflict : t.error);
    } finally { setBusy(false); }
  }
  function control(field: Field) {
    const label = locale === "ta" ? field.label_ta : field.label_en;
    const value = values[field.id] ?? "";
    const update = (next: string) => setValues((current) => ({ ...current, [field.id]: next }));
    if (field.field_type === "textarea") return <label key={field.id}>{label}{field.required ? " *" : ""}<textarea value={value} maxLength={5000} onChange={(event) => update(event.target.value)} /></label>;
    if (field.field_type === "boolean") return <label key={field.id}>{label}{field.required ? " *" : ""}<select value={value} onChange={(event) => update(event.target.value)}><option value="" /><option value="true">{t.yes}</option><option value="false">{t.no}</option></select></label>;
    return <label key={field.id}>{label}{field.required ? " *" : ""}<input type={field.field_type} value={value} maxLength={field.field_type === "text" ? 5000 : undefined} onChange={(event) => update(event.target.value)} /></label>;
  }
  return <section aria-busy={busy}>
    <p className="eyebrow">{t.eyebrow}</p>
    <h1>{form ? (locale === "ta" ? form.title_ta : form.title_en) : t.eyebrow}</h1>
    <p className="application-boundary">{t.draftOnly}</p>
    <p role="status">{busy ? t.saving : message}</p>
    {form && !draft ? <button onClick={() => void start()} disabled={busy}>{t.start}</button> : null}
    {draft ? <><div className="application-progress"><strong>{draft.completion_percent}%</strong><span>{t.completion}</span><small>{t.version}: {draft.version}</small></div>
      <form className="application-form" onSubmit={(event) => { event.preventDefault(); void save(); }}>
        {draft.form.fields.length ? draft.form.fields.map(control) : <p>{t.empty}</p>}
        <button type="submit" disabled={busy}>{t.save}</button>
      </form></> : null}
  </section>;
}
