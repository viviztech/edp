"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { components } from "../../../lib/api-contracts";
import { DefinitionDetails, impactMutation, RecordDetails, words, type Locale, type Mine, type RecordView } from "./content";

type Input = components["schemas"]["ImpactRecordCreate"];
type Draft = { enrollment_id: string; definition_id: string; stage: "baseline" | "outcome"; observed_on: string;
  business_started: boolean; business_active: boolean; jobs_created: string; reason: string };
const blank = (): Draft => ({ enrollment_id: "", definition_id: "", stage: "baseline", observed_on: new Date().toISOString().slice(0, 10), business_started: false, business_active: false, jobs_created: "0", reason: "" });
const key = (item: Pick<RecordView, "enrollment_id" | "stage" | "observed_on">) => `${item.enrollment_id}/${item.stage}/${item.observed_on}`;
function merge<T extends { id: string }>(previous: T[], incoming: T[]) {
  const entries = new Map(previous.map((item) => [item.id, item])); for (const item of incoming) entries.set(item.id, item); return [...entries.values()];
}

export default function ImpactWorkspace({ org, locale }: { org: string; locale: Locale }) {
  const t = words[locale]; const base = `/api/impact/organizations/${org}`;
  const [mine, setMine] = useState<Mine | null>(null); const [draft, setDraft] = useState<Draft>(blank);
  const [editing, setEditing] = useState<RecordView | null>(null); const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false); const [loading, setLoading] = useState(true); const [message, setMessage] = useState("");
  const [failed, setFailed] = useState(false); const [needsRefresh, setNeedsRefresh] = useState(false); const [pending, setPending] = useState<Input | null>(null);
  const mounted = useRef(true); const generation = useRef(0); const lock = useRef(false);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; generation.current += 1; }; }, []);
  useEffect(() => { const warn = (event: BeforeUnloadEvent) => { if (dirty || pending || busy) event.preventDefault(); };
    window.addEventListener("beforeunload", warn); return () => window.removeEventListener("beforeunload", warn); }, [dirty, pending, busy]);
  const initialLoad = useCallback(async () => {
    const attempt = ++generation.current;
    try { const response = await fetch(`${base}/mine?limit=25`, { cache: "no-store" });
      if (!response.ok) throw new Error(response.status === 403 ? "access" : "load"); const data = await response.json() as Mine;
      if (mounted.current && generation.current === attempt) { setMine(data); setFailed(false); setMessage(""); }
    } catch (error) { if (mounted.current && generation.current === attempt) { setFailed(true); setMessage(error instanceof Error && error.message === "access" ? t.access : t.error); } }
    finally { if (mounted.current && generation.current === attempt) setLoading(false); }
  }, [base, t.access, t.error]);
  useEffect(() => { void Promise.resolve().then(initialLoad); }, [initialLoad]);
  const update = <K extends keyof Draft>(field: K, value: Draft[K]) => { setDraft((old) => ({ ...old, [field]: value })); setDirty(true); };
  const accept = (item: RecordView) => { setMine((old) => old && ({ ...old, records: merge(old.records, [item]) })); setEditing(item); setDraft((old) => ({ ...old, reason: "" })); setPending(null); setNeedsRefresh(false); setDirty(false); };
  async function send(body: Input, recovering = false) {
    if (lock.current) return; lock.current = true; setBusy(true); setMessage("");
    try {
      const response = await impactMutation(`${base}/records`, body);
      if (!mounted.current) return;
      if (response.status === 409) { setPending(null); setNeedsRefresh(true); setMessage(t.conflict); return; }
      if (!response.ok) {
        if (response.status >= 500) { setPending(body); setMessage(t.uncertain); }
        else { setPending(null); setMessage(response.status === 403 ? t.access : t.invalid); } return;
      }
      const result = await response.json() as RecordView;
      if (mounted.current) { accept(result); setMessage(recovering ? t.recovered : t.done); }
    } catch { if (mounted.current) { setPending(body); setMessage(t.uncertain); } }
    finally { lock.current = false; if (mounted.current) setBusy(false); }
  }
  async function refresh() {
    if (lock.current) return; lock.current = true; setBusy(true); const attempt = ++generation.current;
    const filters = new URLSearchParams({ limit: "100", enrollment_id: draft.enrollment_id, stage: draft.stage, observed_on: draft.observed_on });
    try { const response = await fetch(`${base}/mine?${filters}`, { cache: "no-store" }); if (!response.ok) throw new Error();
      const data = await response.json() as Mine; if (!mounted.current || generation.current !== attempt) return;
      const current = data.records.filter((item) => key(item) === key(draft)).sort((a, b) => b.revision - a.revision)[0] ?? null;
      setMine((old) => old ? { ...old, records: merge(old.records, data.records), definitions: merge(old.definitions, data.definitions), enrollments: merge(old.enrollments, data.enrollments) } : data);
      setEditing(current); if (current) setDraft((old) => ({ ...old, definition_id: current.definition_id }));
      setNeedsRefresh(false); setMessage(t.refreshed);
    } catch { if (mounted.current) setMessage(t.error); } finally { lock.current = false; if (mounted.current) setBusy(false); }
  }
  async function more(which: "enrollment" | "definition" | "record") {
    const cursor = mine?.[`${which}_next_cursor`]; if (!cursor || lock.current) return; lock.current = true; setBusy(true);
    try { const response = await fetch(`${base}/mine?${which}_cursor=${cursor}&limit=25`, { cache: "no-store" }); if (!response.ok) throw new Error();
      const data = await response.json() as Mine; if (mounted.current) setMine((old) => old && ({ ...old,
        ...(which === "enrollment" ? { enrollments: merge(old.enrollments, data.enrollments), enrollment_next_cursor: data.enrollment_next_cursor } : {}),
        ...(which === "definition" ? { definitions: merge(old.definitions, data.definitions), definition_next_cursor: data.definition_next_cursor } : {}),
        ...(which === "record" ? { records: merge(old.records, data.records), definitions: merge(old.definitions, data.definitions), enrollments: merge(old.enrollments, data.enrollments), record_next_cursor: data.record_next_cursor } : {}),
      }));
    } catch { if (mounted.current) setMessage(t.error); } finally { lock.current = false; if (mounted.current) setBusy(false); }
  }
  function select(item: RecordView | null) {
    if (dirty && !window.confirm(t.discard)) return;
    setEditing(item); setNeedsRefresh(false); setDirty(false); setMessage("");
    setDraft(item ? { enrollment_id: item.enrollment_id, definition_id: item.definition_id, stage: item.stage, observed_on: item.observed_on,
      business_started: item.business_started, business_active: item.business_active, jobs_created: String(item.jobs_created), reason: "" } : blank());
  }
  const definition = mine?.definitions.find((item) => item.id === draft.definition_id);
  const records = [...(mine?.records ?? [])].sort((a, b) => b.observed_on.localeCompare(a.observed_on) || b.revision - a.revision || b.id.localeCompare(a.id));
  const latest = new Map<string, RecordView>(); for (const item of mine?.records ?? []) if ((latest.get(key(item))?.revision ?? 0) < item.revision) latest.set(key(item), item);
  const disabled = busy || loading || !!pending;
  return <><header><h1>{t.title}</h1><p>{t.intro}</p></header>
    <p className="impact-status" role="status">{loading ? t.loading : message}</p>
    {failed && <button disabled={busy || loading} onClick={() => { setLoading(true); void initialLoad(); }}>{t.retry}</button>}
    {pending && <button disabled={busy} onClick={() => void send(pending, true)}>{t.recover}</button>}
    {needsRefresh && <button disabled={disabled} onClick={() => void refresh()}>{t.refresh}</button>}
    {mine && <><section className="impact-panel"><h2>{editing ? t.correct : t.submit}</h2>
      {!mine.enrollments.length && <p>{t.noEnrollments}</p>}
      {!mine.definitions.some((item) => item.state === "published") && !editing && <p>{t.noneDefinitions}</p>}
      {editing && <p>{t.pinned} {t.revision} {editing.revision}</p>}
      {editing && <details><summary>{t.latest}</summary><RecordDetails item={editing} locale={locale} /><p>{editing.reason}</p></details>}
      <form aria-label={t.title} onSubmit={(event) => { event.preventDefault();
        if (disabled || needsRefresh) return;
        const jobs = Number(draft.jobs_created);
        if (!draft.enrollment_id || !draft.definition_id || !draft.reason.trim() || draft.reason.trim().length < 3 || !/^\d+$/.test(draft.jobs_created) || jobs > 100000 || (draft.business_active && !draft.business_started) || !draft.observed_on || draft.observed_on > new Date().toISOString().slice(0, 10)) { setMessage(t.invalid); return; }
        void send({ ...draft, reason: draft.reason.trim(), jobs_created: jobs, expected_revision: editing?.revision ?? 0, request_id: crypto.randomUUID() });
      }}><fieldset disabled={disabled}><div className="impact-grid">
        <label>{t.enrollment}<select name="enrollment_id" required disabled={!!editing} value={draft.enrollment_id} onChange={(event) => update("enrollment_id", event.target.value)}><option value="">{t.choose}</option>
          {mine.enrollments.map((item) => <option key={item.id} value={item.id}>{locale === "ta" ? item.name_ta : item.name_en}</option>)}</select></label>
        <label>{t.definition}<select name="definition_id" required disabled={!!editing} value={draft.definition_id} onChange={(event) => update("definition_id", event.target.value)}><option value="">{t.choose}</option>
          {mine.definitions.filter((item) => item.state === "published" || item.id === draft.definition_id).map((item) => <option key={item.id} value={item.id}>{locale === "ta" ? item.title_ta : item.title_en} · {t.edition} {item.edition}</option>)}</select></label>
        <label>{t.stage}<select name="stage" disabled={!!editing} value={draft.stage} onChange={(event) => update("stage", event.target.value as Draft["stage"])}><option value="baseline">{t.baseline}</option><option value="outcome">{t.outcome}</option></select></label>
        <label>{t.observed}<input name="observed_on" type="date" required max={new Date().toISOString().slice(0, 10)} disabled={!!editing} value={draft.observed_on} onChange={(event) => update("observed_on", event.target.value)} /></label>
      </div>{definition && <DefinitionDetails definition={definition} locale={locale} />}
        <label className="impact-check"><input name="business_started" type="checkbox" checked={draft.business_started} onChange={(event) => update("business_started", event.target.checked)} />{t.started}</label>
        <label className="impact-check"><input name="business_active" type="checkbox" checked={draft.business_active} onChange={(event) => update("business_active", event.target.checked)} />{t.active}</label>
        <label>{t.jobs}<input name="jobs_created" type="number" min="0" max="100000" step="1" required value={draft.jobs_created} onChange={(event) => update("jobs_created", event.target.value)} /></label>
        <label>{t.reason}<textarea name="reason" required minLength={3} maxLength={500} value={draft.reason} onChange={(event) => update("reason", event.target.value)} /></label>
        <button disabled={needsRefresh || !draft.enrollment_id || !draft.definition_id || draft.reason.trim().length < 3}>{t.submit}</button>
        {editing && <button type="button" onClick={() => select(null)}>{t.cancel}</button>}
      </fieldset></form>
      {mine.enrollment_next_cursor && <button disabled={disabled} onClick={() => void more("enrollment")}>{t.more} · {t.enrollment}</button>}
      {mine.definition_next_cursor && <button disabled={disabled} onClick={() => void more("definition")}>{t.more} · {t.definition}</button>}
    </section><section><h2>{t.history}</h2>{!mine.records.length && <p>{t.empty}</p>}
      {records.map((item) => <article key={item.id} className="impact-panel"><p>{t.enrollment}: {(() => { const enrolled = mine.enrollments.find((entry) => entry.id === item.enrollment_id); return enrolled ? locale === "ta" ? enrolled.name_ta : enrolled.name_en : item.enrollment_id; })()}</p><RecordDetails item={item} locale={locale} />
        {mine.definitions.find((entry) => entry.id === item.definition_id) && <DefinitionDetails definition={mine.definitions.find((entry) => entry.id === item.definition_id)!} locale={locale} />}
        <p>{item.reason}</p><small>{new Date(item.created_at).toLocaleString(locale)}</small>
        {latest.get(key(item))?.id === item.id && <><p><button disabled={disabled || !mine.enrollments.some((entry) => entry.id === item.enrollment_id)} onClick={() => select(item)}>{t.correct}</button></p>
          {!mine.enrollments.some((entry) => entry.id === item.enrollment_id) && <p>{t.notEditable}</p>}</>}
      </article>)}
      {mine.record_next_cursor && <button disabled={disabled} onClick={() => void more("record")}>{t.more} · {t.history}</button>}
    </section></>}
  </>;
}
