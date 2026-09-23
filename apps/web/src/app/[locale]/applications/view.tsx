"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { components } from "../../../lib/api-contracts";

type Cycle = components["schemas"]["CycleOpportunityView"];
type Draft = components["schemas"]["DraftView"];
type Submitted = components["schemas"]["SubmittedView"];
type Field = components["schemas"]["FieldView"];
type Application = Draft | Submitted;

const copy = {
  en: {
    eyebrow: "Applicant workspace", title: "My applications", unavailable: "No application cycle is open for this organization.",
    selectCycle: "Open application cycles", closes: "Closes", start: "Start application", save: "Save draft", saving: "Working...", saved: "Draft saved.",
    submit: "Submit application", confirm: "Submit this application? Your answers and acceptances cannot be changed after submission.",
    submitted: "Application submitted", receipt: "Application number", submittedAt: "Submitted", immutable: "This submitted application is read-only.",
    error: "The request could not be completed. Refresh and try again.", incomplete: "Complete every required field before submitting.",
    acknowledgement: "Accept the required declarations and consent before submitting.", conflict: "This application changed in another session. Reload before continuing.",
    completion: "Required fields complete", version: "Application version", empty: "This form has no configured fields.", yes: "Yes", no: "No",
    declarations: "Declarations and consent", history: "Status history", required: "Required",
  },
  ta: {
    eyebrow: "விண்ணப்பதாரர் பணியிடம்", title: "எனது விண்ணப்பங்கள்", unavailable: "இந்த நிறுவனத்திற்கு தற்போது விண்ணப்பச் சுற்று திறக்கப்படவில்லை.",
    selectCycle: "திறந்த விண்ணப்பச் சுற்றுகள்", closes: "முடியும் நேரம்", start: "விண்ணப்பத்தைத் தொடங்கு", save: "வரைவைச் சேமி", saving: "செயல்படுத்துகிறது...", saved: "வரைவு சேமிக்கப்பட்டது.",
    submit: "விண்ணப்பத்தைச் சமர்ப்பி", confirm: "இந்த விண்ணப்பத்தைச் சமர்ப்பிக்கவா? சமர்ப்பித்த பிறகு பதில்களையும் ஒப்புதல்களையும் மாற்ற முடியாது.",
    submitted: "விண்ணப்பம் சமர்ப்பிக்கப்பட்டது", receipt: "விண்ணப்ப எண்", submittedAt: "சமர்ப்பித்த நேரம்", immutable: "சமர்ப்பிக்கப்பட்ட இந்த விண்ணப்பம் படிக்க மட்டும்.",
    error: "கோரிக்கையை முடிக்க முடியவில்லை. புதுப்பித்து மீண்டும் முயலவும்.", incomplete: "சமர்ப்பிக்கும் முன் தேவையான அனைத்துப் புலங்களையும் நிரப்பவும்.",
    acknowledgement: "சமர்ப்பிக்கும் முன் கட்டாய அறிவிப்புகளையும் ஒப்புதலையும் ஏற்கவும்.", conflict: "இந்த விண்ணப்பம் வேறொரு அமர்வில் மாறியுள்ளது. தொடரும் முன் புதுப்பிக்கவும்.",
    completion: "தேவையான புலங்கள் நிறைவு", version: "விண்ணப்பப் பதிப்பு", empty: "இந்தப் படிவத்தில் புலங்கள் இல்லை.", yes: "ஆம்", no: "இல்லை",
    declarations: "அறிவிப்புகள் மற்றும் ஒப்புதல்", history: "நிலை வரலாறு", required: "கட்டாயம்",
  },
} as const;

export default function ApplicationWorkspace({ locale, org }: { locale: "en" | "ta"; org: string }) {
  const t = copy[locale];
  const root = `/api/applications/organizations/${org}`;
  const [cycles, setCycles] = useState<Cycle[]>([]);
  const [cycleId, setCycleId] = useState("");
  const [application, setApplication] = useState<Application | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [accepted, setAccepted] = useState<string[]>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(true);

  const request = useCallback(async <T,>(path: string, method = "GET", body?: unknown): Promise<T> => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (method !== "GET") {
      const tokenResponse = await fetch("/api/session/csrf", { cache: "no-store" });
      if (!tokenResponse.ok) throw new Error("service_unavailable");
      headers["x-csrf-token"] = (await tokenResponse.json()).csrf_token;
    }
    const response = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body), cache: "no-store" });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result?.error?.code ?? (response.status === 409 ? "version_conflict" : "request_failed"));
    return result as T;
  }, []);

  const adopt = useCallback((item: Application | null) => {
    setApplication(item);
    setValues(item ? Object.fromEntries(item.answers.map((answer) => [answer.field_id, answer.value])) : {});
    setAccepted(item?.state === "submitted" ? item.accepted_acknowledgements.map((entry) => entry.definition_id) : []);
  }, []);

  const loadApplication = useCallback(async (selected: string) => {
    try { adopt(await request<Application>(`${root}/cycles/${selected}/application`)); }
    catch (error) {
      if (error instanceof Error && error.message === "not_found") adopt(null);
      else throw error;
    }
  }, [adopt, request, root]);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const result = await request<components["schemas"]["CycleOpportunityList"]>(`${root}/cycles`);
        if (!active) return;
        setCycles(result.items);
        const first = result.items[0]?.id ?? "";
        setCycleId(first);
        if (first) await loadApplication(first);
        else setMessage(t.unavailable);
      } catch { if (active) setMessage(t.error); }
      finally { if (active) setBusy(false); }
    })();
    return () => { active = false; };
  }, [loadApplication, request, root, t.error, t.unavailable]);

  async function selectCycle(id: string) {
    setCycleId(id); setBusy(true); setMessage("");
    try { await loadApplication(id); } catch { setMessage(t.error); } finally { setBusy(false); }
  }
  async function start() {
    if (!cycleId) return;
    setBusy(true); setMessage("");
    try { adopt(await request<Draft>(`${root}/cycles/${cycleId}/draft`, "POST", {})); setMessage(t.saved); }
    catch { setMessage(t.error); } finally { setBusy(false); }
  }
  async function persist(): Promise<Draft> {
    if (!application || application.state !== "draft") throw new Error("not_draft");
    const updated = await request<Draft>(`${root}/draft/${application.id}`, "PATCH", {
      expected_version: application.version,
      answers: application.form.fields.map((field) => ({ field_id: field.id, value: values[field.id] ?? "" })),
    });
    adopt(updated);
    return updated;
  }
  async function save() {
    setBusy(true); setMessage("");
    try { await persist(); setMessage(t.saved); }
    catch (error) { setMessage(error instanceof Error && error.message === "version_conflict" ? t.conflict : t.error); }
    finally { setBusy(false); }
  }
  async function submit() {
    if (!application || application.state !== "draft") return;
    const missingField = application.form.fields.some((field) => field.required && !(values[field.id] ?? "").trim());
    if (missingField) { setMessage(t.incomplete); return; }
    const missingAcceptance = application.form.acknowledgements.some((item) => item.required && !accepted.includes(item.id));
    if (missingAcceptance) { setMessage(t.acknowledgement); return; }
    if (!window.confirm(t.confirm)) return;
    setBusy(true); setMessage("");
    try {
      const saved = await persist();
      const result = await request<Submitted>(`${root}/draft/${saved.id}/submit`, "POST", {
        expected_version: saved.version,
        accepted_acknowledgement_ids: accepted,
      });
      adopt(result); setMessage(t.submitted);
    } catch (error) {
      const code = error instanceof Error ? error.message : "";
      setMessage(code === "version_conflict" ? t.conflict : code === "application_incomplete" ? t.incomplete : code === "acknowledgement_required" ? t.acknowledgement : t.error);
    } finally { setBusy(false); }
  }

  const cycle = useMemo(() => cycles.find((item) => item.id === cycleId), [cycleId, cycles]);
  function control(field: Field) {
    const label = locale === "ta" ? field.label_ta : field.label_en;
    const value = values[field.id] ?? "";
    const disabled = busy || application?.state === "submitted";
    const update = (next: string) => setValues((current) => ({ ...current, [field.id]: next }));
    if (field.field_type === "textarea") return <label key={field.id}>{label}{field.required ? " *" : ""}<textarea required={field.required} disabled={disabled} value={value} maxLength={5000} onChange={(event) => update(event.target.value)} /></label>;
    if (field.field_type === "boolean") return <label key={field.id}>{label}{field.required ? " *" : ""}<select required={field.required} disabled={disabled} value={value} onChange={(event) => update(event.target.value)}><option value="" /><option value="true">{t.yes}</option><option value="false">{t.no}</option></select></label>;
    return <label key={field.id}>{label}{field.required ? " *" : ""}<input required={field.required} disabled={disabled} type={field.field_type} value={value} maxLength={field.field_type === "text" ? 5000 : undefined} onChange={(event) => update(event.target.value)} /></label>;
  }

  return <section className="application-workspace" aria-busy={busy}>
    <p className="eyebrow">{t.eyebrow}</p><h1>{t.title}</h1>
    <p role="status" className="application-message">{busy ? t.saving : message}</p>
    {cycles.length ? <div className="application-cycles" aria-label={t.selectCycle}>
      <h2>{t.selectCycle}</h2>{cycles.map((item) => <button type="button" key={item.id} aria-pressed={cycleId === item.id} disabled={busy} onClick={() => void selectCycle(item.id)}><strong>{locale === "ta" ? item.name_ta : item.name_en}</strong><span>{item.code}</span><small>{t.closes}: {new Date(item.closes_at).toLocaleString(locale)}</small></button>)}
    </div> : !busy ? <p className="application-boundary">{t.unavailable}</p> : null}
    {cycle && !application ? <div className="application-start"><h2>{locale === "ta" ? cycle.name_ta : cycle.name_en}</h2><button type="button" onClick={() => void start()} disabled={busy}>{t.start}</button></div> : null}
    {application?.state === "submitted" ? <div className="application-receipt">
      <p className="eyebrow">{t.submitted}</p><strong>{t.receipt}: {application.application_number}</strong><p>{t.submittedAt}: {new Date(application.submitted_at).toLocaleString(locale)}</p><p>{t.immutable}</p>
    </div> : null}
    {application ? <><div className="application-progress"><strong>{application.completion_percent}%</strong><span>{t.completion}</span><small>{t.version}: {application.version}</small></div>
      <form className="application-form" onSubmit={(event) => { event.preventDefault(); void save(); }}>
        <h2>{locale === "ta" ? application.form.title_ta : application.form.title_en}</h2>
        {application.form.fields.length ? application.form.fields.map(control) : <p>{t.empty}</p>}
        <fieldset className="application-acknowledgements" disabled={busy || application.state === "submitted"}><legend>{t.declarations}</legend>
          {application.form.acknowledgements.map((item) => <label key={item.id}><input type="checkbox" required={item.required} checked={accepted.includes(item.id)} onChange={(event) => setAccepted((current) => event.target.checked ? [...current, item.id] : current.filter((id) => id !== item.id))} /><span>{locale === "ta" ? item.label_ta : item.label_en}{item.required ? ` (${t.required})` : ""}</span></label>)}
        </fieldset>
        {application.state === "draft" ? <div className="application-actions"><button type="submit" disabled={busy}>{t.save}</button><button className="application-submit" type="button" disabled={busy} onClick={() => void submit()}>{t.submit}</button></div> : null}
      </form>
      {application.state === "submitted" ? <div className="application-history"><h2>{t.history}</h2><ol>{application.status_history.map((item) => <li key={`${item.application_version}-${item.created_at}`}><strong>{item.to_state}</strong><time>{new Date(item.created_at).toLocaleString(locale)}</time></li>)}</ol></div> : null}
    </> : null}
  </section>;
}
