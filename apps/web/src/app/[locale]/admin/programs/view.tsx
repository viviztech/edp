"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import type { components } from "../../../../lib/api-contracts";
import { programMessages } from "../../../../lib/program-messages";

type Catalog = components["schemas"]["CatalogView"];
type Program = components["schemas"]["ProgramView"];
type Center = components["schemas"]["CenterView"];
type Cohort = components["schemas"]["CohortView"];
type Cycle = components["schemas"]["CycleView"];
type Definition = components["schemas"]["DefinitionView"];
type Locale = "en" | "ta";
type Resource = "programs" | "centers" | "cohorts" | "cycles";

const empty: Catalog = { programs: [], centers: [], cohorts: [], cycles: [] };

export default function ProgramWorkspace({ org, locale, permissions }: { org: string; locale: Locale; permissions: string[] }) {
  const text = programMessages[locale];
  const root = `/api/programs/organizations/${org}`;
  const [catalog, setCatalog] = useState<Catalog>(empty);
  const [forms, setForms] = useState<Definition[]>([]);
  const [busy, setBusy] = useState(true);
  const [message, setMessage] = useState<string>(text.loading);
  const canProgram = permissions.includes("program.manage");
  const canCohort = permissions.includes("cohort.manage");
  const canCycle = permissions.includes("application.cycle.manage");

  const request = useCallback(async <T,>(path: string, method = "GET", data?: unknown): Promise<T> => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (method !== "GET") {
      const token = await fetch("/api/session/csrf", { cache: "no-store" });
      if (!token.ok) throw new Error("service_unavailable");
      headers["x-csrf-token"] = (await token.json()).csrf_token;
    }
    const response = await fetch(path, { method, headers, body: data === undefined ? undefined : JSON.stringify(data), cache: "no-store" });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body?.error?.code ?? "request_failed");
    return body as T;
  }, []);

  const load = useCallback(async () => {
    const [next, definitions] = await Promise.all([
      request<Catalog>(root + "/catalog"),
      request<components["schemas"]["DefinitionList"]>(`/api/application-definitions/organizations/${org}/definitions`).catch(() => ({ items: [] })),
    ]);
    setCatalog(next);
    setForms(definitions.items.filter((item) => item.state === "published"));
  }, [org, request, root]);

  useEffect(() => {
    let active = true;
    (async () => {
      try { await load(); if (active) setMessage(""); }
      catch { if (active) setMessage(text.error); }
      finally { if (active) setBusy(false); }
    })();
    return () => { active = false; };
  }, [load, text.error]);

  async function run(action: () => Promise<unknown>, form?: HTMLFormElement) {
    setBusy(true);
    try { await action(); await load(); form?.reset(); setMessage(text.saved); }
    catch { setMessage(text.error); }
    finally { setBusy(false); }
  }

  function values(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    return { form, data: Object.fromEntries(new FormData(form)) };
  }

  function create(resource: Resource, event: FormEvent<HTMLFormElement>, transform: (data: Record<string, FormDataEntryValue>) => object = (data) => data) {
    const { form, data } = values(event);
    void run(() => request(`${root}/${resource}`, "POST", transform(data)), form);
  }

  function transition(resource: Resource, item: Program | Center | Cohort | Cycle, target: string) {
    const reason = window.prompt(text.reason);
    if (!reason || reason.trim().length < 3) return;
    void run(() => request(`${root}/${resource}/${item.id}/state`, "POST", { expected_version: item.version, target, reason: reason.trim() }));
  }

  const name = (item: { name_en: string; name_ta: string }) => locale === "ta" ? item.name_ta : item.name_en;
  const field = (label: string, key: string, type = "text", required = true) => <label>{label}<input name={key} type={type} required={required} /></label>;

  return <div className="program-workspace" aria-busy={busy}>
    <p role="status" className="program-message">{busy ? text.loading : message}</p>
    <div className="program-grid">
      <section className="program-panel"><h2>{text.programs}</h2>
        {canProgram && <form className="program-form" onSubmit={(event) => create("programs", event)}>{field(text.code, "code")}{field(text.englishName, "name_en")}{field(text.tamilName, "name_ta")}<button disabled={busy}>{text.create}</button></form>}
        <ul className="program-list">{catalog.programs.map((item) => <li key={item.id}><Record name={name(item)} code={item.code} state={item.state} version={item.version} label={text.version} />{canProgram && <div className="program-actions">{item.state === "draft" && <button onClick={() => transition("programs", item, "active")}>{text.activate}</button>}{item.state === "active" && <button onClick={() => transition("programs", item, "archived")}>{text.archive}</button>}</div>}</li>)}</ul>{!catalog.programs.length && <p>{text.empty}</p>}
      </section>
      <section className="program-panel"><h2>{text.centers}</h2>
        {canProgram && <form className="program-form" onSubmit={(event) => create("centers", event)}>{field(text.code, "code")}{field(text.englishName, "name_en")}{field(text.tamilName, "name_ta")}{field(text.locality, "locality")}<button disabled={busy}>{text.create}</button></form>}
        <ul className="program-list">{catalog.centers.map((item) => <li key={item.id}><Record name={name(item)} code={item.code} state={item.state} version={item.version} label={text.version} /><small>{item.locality}</small>{canProgram && <div className="program-actions"><button onClick={() => transition("centers", item, item.state === "active" ? "inactive" : "active")}>{item.state === "active" ? text.deactivate : text.activate}</button></div>}</li>)}</ul>{!catalog.centers.length && <p>{text.empty}</p>}
      </section>
      <section className="program-panel program-wide"><h2>{text.cohorts}</h2>
        {canCohort && <form className="program-form program-form-wide" onSubmit={(event) => create("cohorts", event, (data) => ({ ...data, capacity: data.capacity ? Number(data.capacity) : null }))}>{field(text.code, "code")}{field(text.englishName, "name_en")}{field(text.tamilName, "name_ta")}<Select label={text.program} name="program_id" options={catalog.programs.filter((item) => item.state === "active").map((item) => [item.id, name(item)])} choose={text.choose} /><Select label={text.center} name="center_id" options={catalog.centers.filter((item) => item.state === "active").map((item) => [item.id, name(item)])} choose={text.choose} />{field(text.starts, "starts_on", "date")}{field(text.ends, "ends_on", "date")}{field(text.capacity, "capacity", "number", false)}<button disabled={busy}>{text.create}</button></form>}
        <ul className="program-list">{catalog.cohorts.map((item) => <li key={item.id}><Record name={name(item)} code={item.code} state={item.state} version={item.version} label={text.version} /><small>{item.starts_on} – {item.ends_on}{item.capacity ? ` · ${item.capacity}` : ""}</small>{canCohort && <div className="program-actions">{item.state === "planned" && <button onClick={() => transition("cohorts", item, "active")}>{text.activate}</button>}{item.state === "active" && <button onClick={() => transition("cohorts", item, "completed")}>{text.complete}</button>}{["planned", "active"].includes(item.state) && <button onClick={() => transition("cohorts", item, "cancelled")}>{text.cancel}</button>}</div>}</li>)}</ul>{!catalog.cohorts.length && <p>{text.empty}</p>}
      </section>
      <section className="program-panel program-wide"><h2>{text.cycles}</h2>
        {canCycle && <form className="program-form program-form-wide" onSubmit={(event) => create("cycles", event, (data) => ({ ...data, cohort_id: data.cohort_id || null, opens_at: new Date(String(data.opens_at)).toISOString(), closes_at: new Date(String(data.closes_at)).toISOString() }))}>{field(text.code, "code")}{field(text.englishName, "name_en")}{field(text.tamilName, "name_ta")}<Select label={text.program} name="program_id" options={catalog.programs.filter((item) => item.state === "active").map((item) => [item.id, name(item)])} choose={text.choose} /><Select label={text.cohort} name="cohort_id" options={catalog.cohorts.filter((item) => ["planned", "active"].includes(item.state)).map((item) => [item.id, name(item)])} choose={text.choose} required={false} /><Select label={text.form} name="form_id" options={forms.map((item) => [item.id, `${item.title_en} v${item.version}`])} choose={text.choose} />{field(text.opens, "opens_at", "datetime-local")}{field(text.closes, "closes_at", "datetime-local")}<button disabled={busy}>{text.create}</button></form>}
        <ul className="program-list">{catalog.cycles.map((item) => <li key={item.id}><Record name={name(item)} code={item.code} state={item.state} version={item.version} label={text.version} /><small>{new Date(item.opens_at).toLocaleString(locale)} – {new Date(item.closes_at).toLocaleString(locale)}</small>{canCycle && <div className="program-actions">{item.state === "draft" && <button onClick={() => transition("cycles", item, "open")}>{text.open}</button>}{item.state === "open" && <button onClick={() => transition("cycles", item, "closed")}>{text.close}</button>}{["draft", "open"].includes(item.state) && <button onClick={() => transition("cycles", item, "cancelled")}>{text.cancel}</button>}</div>}</li>)}</ul>{!catalog.cycles.length && <p>{text.empty}</p>}
      </section>
    </div>
  </div>;
}

function Record({ name, code, state, version, label }: { name: string; code: string; state: string; version: number; label: string }) {
  return <div className="program-record"><div><strong>{name}</strong><small>{code} · {label} {version}</small></div><span className={`program-state program-state-${state}`}>{state}</span></div>;
}

function Select({ label, name, options, choose, required = true }: { label: string; name: string; options: [string, string][]; choose: string; required?: boolean }) {
  return <label>{label}<select name={name} required={required}><option value="">{choose}</option>{options.map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select></label>;
}
