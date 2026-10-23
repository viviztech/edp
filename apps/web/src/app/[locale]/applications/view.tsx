"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { components } from "../../../lib/api-contracts";
import { applicationMessages } from "../../../lib/application-messages";
import ApplicationHistory from "./history";

type Cycle = components["schemas"]["CycleOpportunityView"];
type Draft = components["schemas"]["DraftView"];
type Submitted = components["schemas"]["SubmittedView"];
type Field = components["schemas"]["FieldView"];
type Application = Draft | Submitted;

export default function ApplicationWorkspace({ locale, org, initialCycle }: {
  locale: "en" | "ta"; org?: string; initialCycle?: string;
}) {
  const t = applicationMessages[locale];
  const root = org ? `/api/applications/organizations/${org}` : "";
  const [cycles, setCycles] = useState<Cycle[]>([]);
  const [cyclesLoaded, setCyclesLoaded] = useState(false);
  const [cycleId, setCycleId] = useState(initialCycle ?? "");
  const selectedCycle = useRef(initialCycle ?? "");
  const [application, setApplication] = useState<Application | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [accepted, setAccepted] = useState<string[]>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(Boolean(org));
  const [reload, setReload] = useState(0);
  const [historyRevision, setHistoryRevision] = useState(0);
  const selection = useRef({ value: 0 });

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
    setAccepted(item && item.state !== "draft" ? item.accepted_acknowledgements.map((entry) => entry.definition_id) : []);
  }, []);

  const fetchApplication = useCallback(async (selected: string): Promise<Application | null> => {
    try { return await request<Application>(`${root}/cycles/${selected}/application`); }
    catch (error) {
      if (error instanceof Error && ["not_found", "application_unavailable"].includes(error.message)) return null;
      throw error;
    }
  }, [request, root]);

  useEffect(() => {
    if (!root) return;
    let active = true;
    const counter = selection.current;
    const version = ++counter.value;
    (async () => {
      let available: Cycle[] = [];
      try {
        const result = await request<components["schemas"]["CycleOpportunityList"]>(`${root}/cycles`);
        if (!active || version !== selection.current.value) return;
        available = result.items;
        setCycles(available);
        setCyclesLoaded(true);
      } catch {
        if (!active || version !== selection.current.value) return;
        setMessage(t.error);
      }
      // An explicit saved intake is readable even after discovery stops listing it.
      // Never replace a requested intake with a different open one on failure.
      const selected = selectedCycle.current || available[0]?.id || "";
      selectedCycle.current = selected;
      if (active && version === selection.current.value) setCycleId(selected);
      if (selected) {
        try {
          const item = await fetchApplication(selected);
          if (!active || version !== selection.current.value) return;
          adopt(item);
          if (!item && !available.some((entry) => entry.id === selected)) setMessage(t.selectedUnavailable);
        } catch { if (active && version === selection.current.value) setMessage(t.selectedUnavailable); }
      }
      if (active && version === selection.current.value) setBusy(false);
    })();
    return () => { active = false; counter.value++; };
  }, [adopt, fetchApplication, initialCycle, reload, request, root, t.error, t.selectedUnavailable]);

  const dirty = useMemo(() => {
    if (!application || application.state !== "draft") return false;
    const saved = Object.fromEntries(application.answers.map((answer) => [answer.field_id, answer.value]));
    return accepted.length > 0 || application.form.fields.some((field) => (values[field.id] ?? "") !== (saved[field.id] ?? ""));
  }, [accepted, application, values]);

  useEffect(() => {
    if (!dirty && !busy) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    const guardLink = (event: MouseEvent) => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const link = event.target instanceof Element ? event.target.closest("a[href]") : null;
      if (!(link instanceof HTMLAnchorElement) || link.closest(".application-workspace") || link.target === "_blank" || link.hasAttribute("download")) return;
      const destination = new URL(link.href, window.location.href);
      if (destination.origin !== window.location.origin || (destination.pathname === window.location.pathname && destination.search === window.location.search)) return;
      if (busy || !window.confirm(t.leave)) { event.preventDefault(); event.stopPropagation(); }
    };
    window.addEventListener("beforeunload", warn);
    document.addEventListener("click", guardLink, true);
    return () => { window.removeEventListener("beforeunload", warn); document.removeEventListener("click", guardLink, true); };
  }, [busy, dirty, t.leave]);

  function canNavigate() { return !busy && (!dirty || window.confirm(t.leave)); }

  async function selectCycle(id: string) {
    if (id === cycleId || !canNavigate()) return;
    const version = ++selection.current.value;
    selectedCycle.current = id;
    setCycleId(id); setBusy(true); setMessage(""); adopt(null);
    try {
      const item = await fetchApplication(id);
      if (version === selection.current.value) adopt(item);
    } catch { if (version === selection.current.value) setMessage(t.selectedUnavailable); }
    finally { if (version === selection.current.value) setBusy(false); }
  }

  async function start() {
    if (busy || !cycleId || !cycles.some((item) => item.id === cycleId)) return;
    setBusy(true); setMessage("");
    try {
      adopt(await request<Draft>(`${root}/cycles/${cycleId}/draft`, "POST", {}));
      setMessage(t.saved); setHistoryRevision((value) => value + 1);
    } catch { setMessage(t.error); }
    finally { setBusy(false); }
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
    if (busy || !cycles.some((item) => item.id === cycleId)) return;
    setBusy(true); setMessage("");
    try { await persist(); setMessage(t.saved); setHistoryRevision((value) => value + 1); }
    catch (error) { setMessage(error instanceof Error && error.message === "version_conflict" ? t.conflict : t.error); }
    finally { setBusy(false); }
  }

  async function submit() {
    if (busy || !application || application.state !== "draft" || !cycles.some((item) => item.id === cycleId)) return;
    if (application.form.fields.some((field) => field.required && !(values[field.id] ?? "").trim())) { setMessage(t.incomplete); return; }
    if (application.form.acknowledgements.some((item) => item.required && !accepted.includes(item.id))) { setMessage(t.acknowledgement); return; }
    if (!window.confirm(t.confirm)) return;
    setBusy(true); setMessage("");
    try {
      const saved = await persist();
      const result = await request<Submitted>(`${root}/draft/${saved.id}/submit`, "POST", {
        expected_version: saved.version, accepted_acknowledgement_ids: accepted,
      });
      adopt(result); setMessage(t.submitted); setHistoryRevision((value) => value + 1);
    } catch (error) {
      const code = error instanceof Error ? error.message : "";
      setMessage(code === "version_conflict" ? t.conflict : code === "application_incomplete" ? t.incomplete : code === "acknowledgement_required" ? t.acknowledgement : t.error);
    } finally { setBusy(false); }
  }

  const cycle = cycles.find((item) => item.id === cycleId);
  const editable = application?.state === "draft" && Boolean(cycle);
  function control(field: Field) {
    const label = locale === "ta" ? field.label_ta : field.label_en;
    const value = values[field.id] ?? "";
    const disabled = busy || !editable;
    const update = (next: string) => setValues((current) => ({ ...current, [field.id]: next }));
    if (field.field_type === "textarea") return <label key={field.id}>{label}{field.required ? " *" : ""}<textarea required={field.required} disabled={disabled} value={value} maxLength={5000} onChange={(event) => update(event.target.value)} /></label>;
    if (field.field_type === "boolean") return <label key={field.id}>{label}{field.required ? " *" : ""}<select required={field.required} disabled={disabled} value={value} onChange={(event) => update(event.target.value)}><option value="" /><option value="true">{t.yes}</option><option value="false">{t.no}</option></select></label>;
    return <label key={field.id}>{label}{field.required ? " *" : ""}<input required={field.required} disabled={disabled} type={field.field_type} value={value} maxLength={field.field_type === "text" ? 5000 : undefined} onChange={(event) => update(event.target.value)} /></label>;
  }

  return <section className="application-workspace" aria-busy={busy}>
    <p className="eyebrow">{t.eyebrow}</p><h1>{t.title}</h1>
    <p role="status" className="application-message">{busy ? t.saving : message}</p>
    <ApplicationHistory locale={locale} refreshKey={historyRevision} currentId={application?.id} canNavigate={canNavigate} navigationBlocked={busy} />
    {cycles.length ? <div className="application-cycles" aria-label={t.selectCycle}>
      <h2>{t.selectCycle}</h2>{cycles.map((item) => <button type="button" key={item.id} aria-pressed={cycleId === item.id} disabled={busy} onClick={() => void selectCycle(item.id)}><strong>{locale === "ta" ? item.name_ta : item.name_en}</strong><span>{item.code}</span><small>{t.closes}: {new Date(item.closes_at).toLocaleString(locale)}</small></button>)}
    </div> : !busy && (!org || cyclesLoaded) ? <p className="application-boundary">{org ? t.unavailable : t.noOrganization}</p> : null}
    {application && cyclesLoaded && !cycle && !busy && <p className="application-closed">{t.closed}</p>}
    {org && <button type="button" className="application-reload" disabled={busy} onClick={() => {
      if (!canNavigate()) return;
      adopt(null); setCycles([]); setCyclesLoaded(false); setBusy(true); setMessage(""); setReload((value) => value + 1); setHistoryRevision((value) => value + 1);
    }}>{t.reload}</button>}
    {cycle && !application && !busy && !message ? <div className="application-start"><h2>{locale === "ta" ? cycle.name_ta : cycle.name_en}</h2><button type="button" onClick={() => void start()} disabled={busy}>{t.start}</button></div> : null}
    {application && application.state !== "draft" ? <div className="application-receipt">
      <p className="eyebrow">{t.states[application.state]}</p><strong>{t.receipt}: {application.application_number}</strong><p>{t.submittedAt}: {new Date(application.submitted_at).toLocaleString(locale)}</p><p>{t.immutable}</p>
    </div> : null}
    {application ? <><div className="application-progress"><strong>{application.completion_percent}%</strong><span>{t.completion}</span><small>{t.version}: {application.version}</small></div>
      <form className="application-form" onSubmit={(event) => { event.preventDefault(); void save(); }}>
        <h2>{locale === "ta" ? application.form.title_ta : application.form.title_en}</h2>
        {application.form.fields.length ? application.form.fields.map(control) : <p>{t.empty}</p>}
        <fieldset className="application-acknowledgements" disabled={busy || !editable}><legend>{t.declarations}</legend>
          {application.form.acknowledgements.map((item) => <label key={item.id}><input type="checkbox" required={item.required} checked={accepted.includes(item.id)} onChange={(event) => setAccepted((current) => event.target.checked ? [...current, item.id] : current.filter((id) => id !== item.id))} /><span>{locale === "ta" ? item.label_ta : item.label_en}{item.required ? ` (${t.required})` : ""}</span></label>)}
        </fieldset>
        {editable ? <div className="application-actions"><button type="submit" disabled={busy}>{t.save}</button><button className="application-submit" type="button" disabled={busy} onClick={() => void submit()}>{t.submit}</button></div> : null}
      </form>
      {application.state !== "draft" ? <div className="application-history"><h2>{t.history}</h2><ol>{application.status_history.map((item) => <li key={`${item.application_version}-${item.created_at}`}><strong>{t.states[item.to_state as keyof typeof t.states] ?? item.to_state}</strong><time dateTime={item.created_at}>{new Date(item.created_at).toLocaleString(locale)}</time></li>)}</ol></div> : null}
    </> : null}
  </section>;
}
