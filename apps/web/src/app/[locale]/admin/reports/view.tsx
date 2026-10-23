"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { components } from "../../../../lib/api-contracts";
import { impactMutation, words, type Dashboard, type ExportJob, type Locale, type Snapshot } from "../../impact/content";
import Definitions from "./definitions";
import { Comparison, Evidence } from "./evidence";

type Filters = components["schemas"]["ReportFilters"];
type Options = components["schemas"]["ReportOptions"];
type Summary = components["schemas"]["ReportSnapshotSummary"];
type Pending = { kind: "snapshot"; body: components["schemas"]["ReportSnapshotCreate"] } | { kind: "export"; body: components["schemas"]["ReportExportCreate"] };
const initialFilters = (): Filters => { const date = new Date(); const through = date.toISOString().slice(0, 10); date.setUTCDate(date.getUTCDate() - 29); return { from_date: date.toISOString().slice(0, 10), through_date: through, program_id: null, cohort_id: null }; };
function search(filters: Filters) { const query = new URLSearchParams({ from_date: filters.from_date, through_date: filters.through_date }); if (filters.program_id) query.set("program_id", filters.program_id); if (filters.cohort_id) query.set("cohort_id", filters.cohort_id); return query.toString(); }
function merge<T extends { id: string }>(old: T[], incoming: T[]) { const items = new Map(old.map((item) => [item.id, item])); for (const item of incoming) items.set(item.id, item); return [...items.values()]; }

export default function ReportsWorkspace({ org, locale, canView, canExport, canManage }: { org: string; locale: Locale; canView: boolean; canExport: boolean; canManage: boolean }) {
  const t = words[locale]; const base = `/api/reports/organizations/${org}`;
  const [draft, setDraft] = useState<Filters>(initialFilters); const [live, setLive] = useState<Dashboard | null>(null);
  const [options, setOptions] = useState<Options | null>(null); const [snapshots, setSnapshots] = useState<Summary[]>([]); const [snapshotCursor, setSnapshotCursor] = useState<string | null>(null);
  const [exports, setExports] = useState<ExportJob[]>([]); const [exportCursor, setExportCursor] = useState<string | null>(null);
  const [selected, setSelected] = useState<Snapshot | null>(null); const [comparison, setComparison] = useState<Snapshot | null>(null); const [comparisonId, setComparisonId] = useState("");
  const [reason, setReason] = useState(""); const [pending, setPending] = useState<Pending | null>(null);
  const [busy, setBusy] = useState(false); const [loading, setLoading] = useState(canView); const [message, setMessage] = useState(""); const [failed, setFailed] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const mounted = useRef(true); const loadGeneration = useRef(0); const selectionGeneration = useRef(0); const comparisonGeneration = useRef(0); const optionsGeneration = useRef(0); const lock = useRef(false);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; loadGeneration.current += 1; selectionGeneration.current += 1; comparisonGeneration.current += 1; optionsGeneration.current += 1; }; }, []);
  useEffect(() => { const warn = (event: BeforeUnloadEvent) => { if (pending || busy || reason.trim()) event.preventDefault(); }; window.addEventListener("beforeunload", warn); return () => window.removeEventListener("beforeunload", warn); }, [pending, reason, busy]);
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 30000); return () => clearInterval(timer); }, []);
  const load = useCallback(async (filters: Filters, includeLists = false) => {
    const attempt = ++loadGeneration.current;
    try {
      const responses = await Promise.all([fetch(`${base}/dashboard?${search(filters)}`, { cache: "no-store" }),
        ...(includeLists ? [fetch(`${base}/options?limit=25`, { cache: "no-store" }), fetch(`${base}/snapshots?limit=25`, { cache: "no-store" }), ...(canExport ? [fetch(`${base}/exports?limit=25`, { cache: "no-store" })] : [])] : [])]);
      if (responses.some((response) => !response.ok)) throw new Error(responses.some((response) => response.status === 403) ? "access" : "load");
      const [dashboard, choices, saved, jobs] = await Promise.all(responses.map((response) => response.json())) as [Dashboard, Options?, components["schemas"]["ReportSnapshotList"]?, components["schemas"]["ReportExportList"]?];
      if (mounted.current && loadGeneration.current === attempt) {
        setLive(dashboard); setSelected(null); selectionGeneration.current += 1; setFailed(false); setMessage("");
        if (choices) setOptions(choices); if (saved) { setSnapshots(saved.items); setSnapshotCursor(saved.next_cursor); } if (jobs) { setExports(jobs.items); setExportCursor(jobs.next_cursor); }
      }
    } catch (error) { if (mounted.current && loadGeneration.current === attempt) { setFailed(true); setMessage(error instanceof Error && error.message === "access" ? t.access : t.error); } }
    finally { if (mounted.current && loadGeneration.current === attempt) setLoading(false); }
  }, [base, canExport, t.access, t.error]);
  useEffect(() => { if (canView) void Promise.resolve().then(() => load(initialFilters(), true)); }, [load, canView]);
  async function optionsPage(which: "program" | "cohort") {
    const cursor = options?.[`${which}_next_cursor`]; if (!cursor || lock.current) return; lock.current = true; setBusy(true); const attempt = ++optionsGeneration.current;
    try { const response = await fetch(`${base}/options?${which}_cursor=${cursor}&limit=25`, { cache: "no-store" }); if (!response.ok) throw new Error(); const batch = await response.json() as Options;
      if (mounted.current && optionsGeneration.current === attempt) setOptions((old) => old && ({ ...old,
        ...(which === "program" ? { programs: merge(old.programs, batch.programs), program_next_cursor: batch.program_next_cursor } : { cohorts: merge(old.cohorts, batch.cohorts), cohort_next_cursor: batch.cohort_next_cursor }),
      }));
    } catch { if (mounted.current) setMessage(t.error); } finally { lock.current = false; if (mounted.current) setBusy(false); }
  }
  async function listPage(which: "snapshots" | "exports") {
    const cursor = which === "snapshots" ? snapshotCursor : exportCursor; if (!cursor || lock.current) return; lock.current = true; setBusy(true);
    try { const response = await fetch(`${base}/${which}?cursor=${cursor}&limit=25`, { cache: "no-store" }); if (!response.ok) throw new Error();
      if (which === "snapshots") { const batch = await response.json() as components["schemas"]["ReportSnapshotList"]; if (mounted.current) { setSnapshots((old) => merge(old, batch.items)); setSnapshotCursor(batch.next_cursor); } }
      else { const batch = await response.json() as components["schemas"]["ReportExportList"]; if (mounted.current) { setExports((old) => merge(old, batch.items)); setExportCursor(batch.next_cursor); } }
    } catch { if (mounted.current) setMessage(t.error); } finally { lock.current = false; if (mounted.current) setBusy(false); }
  }
  async function selectSnapshot(id: string, compare = false) {
    if (lock.current || pending) return;
    const attempt = compare ? ++comparisonGeneration.current : ++selectionGeneration.current;
    if (compare) setComparisonId(id);
    if (!id) { if (compare) setComparison(null); else setSelected(null); return; }
    lock.current = true; setBusy(true); setMessage("");
    try { const response = await fetch(`${base}/snapshots/${id}`, { cache: "no-store" }); if (!response.ok) throw new Error(); const item = await response.json() as Snapshot;
      if (mounted.current && attempt === (compare ? comparisonGeneration.current : selectionGeneration.current)) { if (compare) setComparison(item); else setSelected(item); }
    } catch { if (mounted.current && attempt === (compare ? comparisonGeneration.current : selectionGeneration.current)) { if (compare) { setComparison(null); setComparisonId(""); } setMessage(t.error); } }
    finally { lock.current = false; if (mounted.current && attempt === (compare ? comparisonGeneration.current : selectionGeneration.current)) setBusy(false); }
  }
  async function write(request: Pending, recovering = false) {
    if (lock.current) return; lock.current = true; setBusy(true); setMessage("");
    try { const response = await impactMutation(`${base}/${request.kind === "snapshot" ? "snapshots" : "exports"}`, request.body);
      if (!mounted.current) return;
      if (!response.ok) { setPending(response.status >= 500 ? request : null); setMessage(response.status === 403 ? t.access : response.status >= 500 ? t.uncertain : t.error); return; }
      if (request.kind === "snapshot") {
        const item = await response.json() as Snapshot; if (!mounted.current) return;
        setSelected(item); selectionGeneration.current += 1; setSnapshots((old) => merge(old, [{ id: item.id, created_at: item.created_at, request_id: item.request_id, filters: item.dashboard.filters, dictionary_version: item.dashboard.dictionary_version, generated_at: item.dashboard.generated_at }]));
        setMessage(recovering ? t.recovered : t.snapshotSaved);
      } else { const item = await response.json() as ExportJob; if (!mounted.current) return; setExports((old) => merge(old, [item])); setReason(""); setMessage(recovering ? t.recovered : t.exportDone); }
      setPending(null);
    } catch { if (mounted.current) { setPending(request); setMessage(t.uncertain); } }
    finally { lock.current = false; if (mounted.current) setBusy(false); }
  }
  async function download(item: ExportJob) {
    if (lock.current || pending) return; lock.current = true; setBusy(true); setMessage("");
    try { const access = await impactMutation(`${base}/exports/${item.id}/access`, {}); if (!access.ok) throw new Error();
      const capability = await access.json() as components["schemas"]["ReportExportAccess"];
      if (!/^[A-Za-z0-9_-]{43}$/.test(capability.token)) throw new Error();
      const response = await fetch(`${base}/exports/${item.id}/download/${capability.token}`, { cache: "no-store", referrerPolicy: "no-referrer" });
      if (!response.ok || !response.headers.get("content-type")?.startsWith("text/csv")) throw new Error();
      const blob = await response.blob(); if (!mounted.current) return; if (blob.size > 262144) throw new Error();
      const url = URL.createObjectURL(blob); const anchor = document.createElement("a"); anchor.href = url; anchor.download = "impact-report.csv"; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); setMessage(t.downloaded);
    } catch { if (mounted.current) setMessage(t.error); } finally { lock.current = false; if (mounted.current) setBusy(false); }
  }
  const disabled = busy || loading || !!pending; const dashboard = selected?.dashboard ?? live;
  const labelSnapshot = (item: Summary) => `${item.filters.from_date} — ${item.filters.through_date} · ${new Date(item.created_at).toLocaleString(locale)}`;
  return <><header><h1>{t.reports}</h1><p>{t.reportIntro}</p></header>
    {canView && <><form aria-label={t.filters} className="impact-panel" onSubmit={(event) => { event.preventDefault(); if (disabled) return;
      const days = (Date.parse(`${draft.through_date}T00:00:00Z`) - Date.parse(`${draft.from_date}T00:00:00Z`)) / 86400000;
      if (!Number.isFinite(days) || days < 0 || days > 365 || draft.through_date > new Date().toISOString().slice(0, 10)) { setMessage(t.invalid); return; }
      setLoading(true); void load(draft);
    }}><p>{t.window}</p><fieldset disabled={disabled}><div className="impact-grid">
      <label>{t.from}<input type="date" name="from_date" required max={new Date().toISOString().slice(0, 10)} value={draft.from_date} onChange={(event) => setDraft((old) => ({ ...old, from_date: event.target.value }))} /></label>
      <label>{t.through}<input type="date" name="through_date" required max={new Date().toISOString().slice(0, 10)} value={draft.through_date} onChange={(event) => setDraft((old) => ({ ...old, through_date: event.target.value }))} /></label>
      <label>{t.program}<select name="program_id" value={draft.program_id ?? ""} onChange={(event) => setDraft((old) => ({ ...old, program_id: event.target.value || null, cohort_id: null }))}><option value="">{t.allPrograms}</option>
        {options?.programs.map((item) => <option key={item.id} value={item.id}>{locale === "ta" ? item.name_ta : item.name_en}</option>)}</select></label>
      <label>{t.cohort}<select name="cohort_id" value={draft.cohort_id ?? ""} onChange={(event) => { const id = event.target.value; const chosen = options?.cohorts.find((item) => item.id === id); setDraft((old) => ({ ...old, cohort_id: id || null, program_id: chosen?.program_id ?? old.program_id })); }}><option value="">{t.allCohorts}</option>
        {options?.cohorts.filter((item) => !draft.program_id || item.program_id === draft.program_id).map((item) => <option key={item.id} value={item.id}>{locale === "ta" ? item.name_ta : item.name_en}</option>)}</select></label>
    </div><button>{t.apply}</button></fieldset>
      {options?.program_next_cursor && <button type="button" disabled={disabled} onClick={() => void optionsPage("program")}>{t.more} · {t.program}</button>}
      {options?.cohort_next_cursor && <button type="button" disabled={disabled} onClick={() => void optionsPage("cohort")}>{t.more} · {t.cohort}</button>}
    </form><p role="status" className="impact-status">{loading ? t.loading : message}</p>
      {failed && <button disabled={disabled} onClick={() => { setLoading(true); void load(draft, !live); }}>{t.retry}</button>}
      {pending && <button disabled={busy || loading} onClick={() => void write(pending, true)}>{t.recover}</button>}
      <section className="impact-panel"><h2>{t.snapshots}</h2><button disabled={disabled || !live} onClick={() => void write({ kind: "snapshot", body: { ...live!.filters, request_id: crypto.randomUUID() } })}>{t.freeze}</button>
        <label>{t.view}<select value={selected?.id ?? ""} disabled={disabled} onChange={(event) => void selectSnapshot(event.target.value)}><option value="">{t.live}</option>{snapshots.map((item) => <option key={item.id} value={item.id}>{labelSnapshot(item)}</option>)}</select></label>
        <label>{t.compare}<select value={comparisonId} disabled={disabled} onChange={(event) => void selectSnapshot(event.target.value, true)}><option value="">{t.noComparison}</option>{snapshots.map((item) => <option key={item.id} value={item.id}>{labelSnapshot(item)}</option>)}</select></label>
        {snapshotCursor && <button disabled={disabled} onClick={() => void listPage("snapshots")}>{t.more} · {t.snapshots}</button>}
      </section>
      {dashboard && <Evidence dashboard={dashboard} locale={locale} />}
      {dashboard && comparison && <Comparison current={dashboard} previous={comparison.dashboard} locale={locale} />}
      <section className="impact-panel"><h2>{t.exports}</h2>{!canExport ? <p>{t.exportUnavailable}</p> : <>
        {!selected && <p>{t.snapshotRequired}</p>}<form aria-label={t.exports} onSubmit={(event) => { event.preventDefault(); if (!selected || disabled || reason.trim().length < 3) return; void write({ kind: "export", body: { snapshot_id: selected.id, request_id: crypto.randomUUID(), reason: reason.trim() } }); }}>
          <label>{t.exportReason}<textarea required minLength={3} maxLength={500} disabled={disabled} value={reason} onChange={(event) => setReason(event.target.value)} /></label><button disabled={disabled || !selected || reason.trim().length < 3}>{t.exportCreate}</button></form>
        {!exports.length && <p>{t.empty}</p>}{exports.map((item) => <article key={item.id} className="impact-panel"><p>{new Date(item.created_at).toLocaleString(locale)} · {t.rows}: {item.row_count} · {t.bytes}: {item.byte_count}</p>
          <p>{t.expires}: {new Date(item.expires_at).toLocaleString(locale)}</p><button disabled={disabled || Date.parse(item.expires_at) <= now} onClick={() => void download(item)}>{Date.parse(item.expires_at) <= now ? t.expired : t.download}</button></article>)}
        {exportCursor && <button disabled={disabled} onClick={() => void listPage("exports")}>{t.more} · {t.exports}</button>}
      </>}</section>
    </>}
    {canManage && <Definitions org={org} locale={locale} />}
  </>;
}
