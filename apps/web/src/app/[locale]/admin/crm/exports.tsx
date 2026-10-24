"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { components } from "../../../../lib/api-contracts";
import { crmExportMessages } from "../../../../lib/crm-export-messages";
import type { CrmLocale } from "../../../../lib/crm-messages";

type ExportJob = components["schemas"]["ExportJobView"];
type ExportHistory = components["schemas"]["ExportJobList"];
const pollInterval = 3000, maximumPolls = 20;
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
class ExportRequestError extends Error {
  constructor(public status: number, public code = "") { super("export_request_failed"); }
}
async function responseError(response: Response) {
  const body = await response.json().catch(() => null);
  return new ExportRequestError(response.status, typeof body?.error?.code === "string" ? body.error.code : "");
}
function parseJob(body: unknown): ExportJob {
  if (!body || typeof body !== "object") throw new Error();
  const value = body as Partial<ExportJob>;
  if (typeof value.id !== "string" || !uuid.test(value.id)
    || !["queued", "running", "completed", "failed"].includes(value.status ?? "")
    || !Number.isInteger(value.row_count) || value.row_count! < 0 || typeof value.error_code !== "string"
    || typeof value.expires_at !== "string" || !Number.isFinite(Date.parse(value.expires_at))
    || value.created_at != null && (typeof value.created_at !== "string" || !Number.isFinite(Date.parse(value.created_at)))) throw new Error();
  return value as ExportJob;
}
async function readJob(response: Response) { return parseJob(await response.json()); }
async function readHistory(response: Response): Promise<ExportHistory> {
  const body: unknown = await response.json();
  if (!body || typeof body !== "object") throw new Error();
  const value = body as Partial<ExportHistory>;
  if (!Array.isArray(value.items) || value.items.length > 25
    || value.next_cursor !== null && (typeof value.next_cursor !== "string" || !uuid.test(value.next_cursor))) throw new Error();
  return { items: value.items.map(parseJob), next_cursor: value.next_cursor };
}
async function historyRequest(root: string, continuation: string | null = null) {
  const query = new URLSearchParams({ limit: "25", ...(continuation ? { cursor: continuation } : {}) });
  const response = await fetch(`${root}?${query}`, { cache: "no-store" });
  if (!response.ok) throw new ExportRequestError(response.status);
  return readHistory(response);
}

export default function CrmExports({ org, locale, blocked = false }: { org: string; locale: CrmLocale; blocked?: boolean }) {
  const t = crmExportMessages[locale], root = `/api/crm/organizations/${org}/exports`;
  const [job, setJob] = useState<ExportJob | null>(null);
  const [busy, setBusy] = useState(false), [verified, setVerified] = useState(false);
  const [uncertain, setUncertain] = useState(false), [paused, setPaused] = useState(false);
  const [history, setHistory] = useState<ExportJob[]>([]), [cursor, setCursor] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(true), [historyReady, setHistoryReady] = useState(false);
  const [historyMessage, setHistoryMessage] = useState("");
  const [message, setMessage] = useState("");
  const [now, setNow] = useState(() => Date.now());
  const lock = useRef(false), mounted = useRef(true), polls = useRef(0);
  const historyLock = useRef(false), historyGeneration = useRef(0), authorizationEpoch = useRef(0);
  const expiry = job ? Date.parse(job.expires_at) : Infinity;
  const expired = !!job && (!Number.isFinite(expiry) || expiry <= now);
  const processing = !!job && !expired && (job.status === "queued" || job.status === "running");
  const knownProcessing = history.some(value => Date.parse(value.expires_at) > now && ["queued", "running"].includes(value.status));
  const nextExpiry = Math.min(expiry > now ? expiry : Infinity, ...history.map(value => Date.parse(value.expires_at)).filter(value => value > now));

  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    if (!Number.isFinite(nextExpiry)) return;
    const timer = window.setTimeout(() => setNow(Date.now()), Math.min(Math.max(1, nextExpiry - Date.now()), 2147483647));
    return () => window.clearTimeout(timer);
  }, [nextExpiry, now]);

  const acceptHistory = useCallback((result: ExportHistory, continuation: string | null) => {
    setHistory(previous => continuation ? [...previous, ...result.items.filter(value => !previous.some(old => old.id === value.id))] : result.items);
    setCursor(result.next_cursor); setHistoryReady(true); setHistoryMessage(""); setNow(Date.now());
  }, []);
  const rejectHistory = useCallback((error: unknown) => {
    setHistoryReady(false);
    const denied = error instanceof ExportRequestError && [401, 403, 404].includes(error.status);
    if (denied) { authorizationEpoch.current++; setHistory([]); setCursor(null); setJob(null); setVerified(false); }
    setHistoryMessage(error instanceof ExportRequestError && error.status === 401 ? t.sessionExpired : denied ? t.noAccess : t.historyFailed);
  }, [t.historyFailed, t.noAccess, t.sessionExpired]);

  useEffect(() => {
    let active = true;
    const generation = ++historyGeneration.current;
    historyLock.current = true;
    historyRequest(root).then(result => {
      if (active && mounted.current && generation === historyGeneration.current) acceptHistory(result, null);
    }).catch(error => {
      if (active && mounted.current && generation === historyGeneration.current) rejectHistory(error);
    }).finally(() => {
      if (active && mounted.current && generation === historyGeneration.current) { historyLock.current = false; setHistoryLoading(false); }
    });
    return () => { active = false; historyLock.current = false; };
  }, [acceptHistory, rejectHistory, root]);
  async function loadHistory(continuation: string | null = null) {
    if (historyLock.current || blocked) return;
    historyLock.current = true;
    const generation = ++historyGeneration.current;
    setHistoryLoading(true); setHistoryMessage(""); setVerified(false);
    try {
      const result = await historyRequest(root, continuation);
      if (mounted.current && generation === historyGeneration.current) acceptHistory(result, continuation);
    } catch (error) {
      if (mounted.current && generation === historyGeneration.current) rejectHistory(error);
    } finally {
      if (mounted.current && generation === historyGeneration.current) { historyLock.current = false; setHistoryLoading(false); }
    }
  }

  function failure(error: unknown, fallback: string) {
    return error instanceof ExportRequestError
      ? error.status === 401 ? t.sessionExpired : [403, 404].includes(error.status) ? t.noAccess : fallback
      : fallback;
  }

  async function request(separate = false) {
    if (lock.current || blocked || processing || knownProcessing || !historyReady || historyLoading || (uncertain && !separate)) return;
    lock.current = true; setBusy(true); setMessage(""); setJob(null); setVerified(false); setPaused(false);
    let posted = false;
    try {
      const csrf = await fetch("/api/session/csrf", { cache: "no-store" });
      if (!csrf.ok) throw new ExportRequestError(csrf.status);
      const token: unknown = (await csrf.json()).csrf_token;
      if (typeof token !== "string" || !token || token.length > 128) throw new Error();
      posted = true;
      const response = await fetch(root, { method: "POST", cache: "no-store", headers: {
        "Content-Type": "application/json", "x-csrf-token": token,
      }, body: "{}" });
      if (!response.ok) throw await responseError(response);
      const result = await readJob(response);
      if (!mounted.current) return;
      setJob(result); setNow(Date.now()); setVerified(true); setUncertain(false); polls.current = 0;
      setHistory(previous => [result, ...previous.filter(value => value.id !== result.id)]);
    } catch (error) {
      if (!mounted.current) return;
      // There is no idempotent request/replay contract for export creation.
      // A lost or server-error response may follow a committed job; never retry it automatically.
      const unavailable = error instanceof ExportRequestError && error.code === "export_retention_unconfigured";
      const ambiguous = posted && !unavailable && (!(error instanceof ExportRequestError) || error.status >= 500);
      setUncertain(ambiguous); setMessage(ambiguous ? "" : unavailable ? t.unavailable : failure(error, t.requestFailed));
      if (ambiguous) await loadHistory();
    } finally {
      lock.current = false;
      if (mounted.current) setBusy(false);
    }
  }

  const inspect = useCallback(async (id: string, automatic = false, selecting = false) => {
    if (lock.current || blocked) return;
    const epoch = authorizationEpoch.current;
    lock.current = true; setBusy(true); setMessage("");
    if (selecting) { setJob(null); setVerified(false); }
    try {
      const response = await fetch(`${root}/${id}`, { cache: "no-store" });
      if (!response.ok) throw new ExportRequestError(response.status);
      const result = await readJob(response);
      if (result.id !== id) throw new Error();
      if (!mounted.current || epoch !== authorizationEpoch.current) return;
      setJob(result); setNow(Date.now()); setVerified(true);
      setHistory(previous => previous.map(value => value.id === result.id ? result : value));
      if (selecting) setUncertain(false);
      if (!automatic) { polls.current = 0; setPaused(false); }
      else if (polls.current >= maximumPolls) setPaused(true);
    } catch (error) {
      if (!mounted.current) return;
      setVerified(false); setPaused(true);
      setMessage(error instanceof ExportRequestError && error.status === 401 ? t.sessionExpired
        : error instanceof ExportRequestError && [403, 404].includes(error.status) ? t.noAccess : t.checkFailed);
    } finally {
      lock.current = false;
      if (mounted.current) setBusy(false);
    }
  }, [blocked, root, t.checkFailed, t.noAccess, t.sessionExpired]);

  useEffect(() => {
    if (!job || !processing || !verified || busy || blocked || paused || historyLoading) return;
    const timer = window.setTimeout(() => { polls.current++; void inspect(job.id, true); }, pollInterval);
    return () => window.clearTimeout(timer);
  }, [blocked, busy, historyLoading, inspect, job, paused, processing, verified]);

  const failureHint = job?.error_code === "requester_unavailable" ? t.requesterUnavailable
    : job?.error_code === "retry_exhausted" ? t.retryExhausted
    : job?.error_code === "request_expired" || job?.error_code === "expired" ? t.expiredHint
    : job?.error_code === "row_limit_exceeded" || job?.error_code === "output_too_large" ? t.tooLarge : t.failedHint;

  const creatingDisabled = busy || blocked || processing || knownProcessing || !historyReady || historyLoading;
  return <section className="crm-export" aria-label={t.title} aria-busy={busy || historyLoading}>
    <div>
      <h3 className="eyebrow">{t.title}</h3>
      <div role="group" aria-label={t.selected}><div role="status">
        {job && <>
          <p>{!verified && !expired && <>{t.lastStatus}: </>}<strong>{expired ? t.expired : t[job.status]}</strong></p>
          <p>{expired ? t.expiredHint : job.status === "queued" ? job.error_code ? t.retryHint : t.queuedHint
            : job.status === "running" ? t.runningHint : job.status === "failed" ? failureHint : `${t.rows}: ${job.row_count.toLocaleString(locale)}`}</p>
          {!expired && Number.isFinite(expiry) && <p>{t.expires}: <time dateTime={job.expires_at}>{new Date(job.expires_at).toLocaleString(locale)}</time></p>}
          <p>{t.reference}: <span style={{ overflowWrap: "anywhere" }}>{job.id}</span></p>
        </>}
        {busy && <p>{t.working}</p>}
        {message && <p>{message}</p>}
        {paused && processing && verified && <p>{t.paused}</p>}
      </div></div>
      {uncertain && <p role="alert">{t.uncertain}</p>}
      <section aria-label={t.history}>
        <h4>{t.history}</h4>
        <p role="status">{historyLoading ? t.historyLoading : historyMessage}</p>
        {historyReady && !history.length && <p>{t.historyEmpty}</p>}
        <ul>{history.map(value => <li key={value.id}>
          <button type="button" disabled={busy || blocked || historyLoading} aria-pressed={job?.id === value.id}
            style={{ overflowWrap: "anywhere" }} onClick={() => void inspect(value.id, false, true)}>{t.open}: {value.id}</button>
          <p>{t.status}: {Date.parse(value.expires_at) <= now ? t.expired : t[value.status]}</p>
          {value.created_at && <p>{t.created}: <time dateTime={value.created_at}>{new Date(value.created_at).toLocaleString(locale)}</time></p>}
        </li>)}</ul>
        <div className="actions">
          <button type="button" disabled={busy || blocked || historyLoading} onClick={() => void loadHistory()}>{t.refreshHistory}</button>
          {cursor && <button type="button" disabled={busy || blocked || historyLoading} onClick={() => void loadHistory(cursor)}>{t.moreHistory}</button>}
        </div>
      </section>
    </div>
    <div className="actions">
      <button disabled={creatingDisabled || uncertain} onClick={() => void request()}>{t.request}</button>
      {uncertain && <button disabled={creatingDisabled} onClick={() => void request(true)}>{t.separate}</button>}
      {job && <button disabled={busy || blocked || expired} onClick={() => void inspect(job.id)}>{t.check}</button>}
      {job?.status === "completed" && verified && !busy && !expired && <a className="crm-download" href={`${root}/${job.id}/download`}>{t.download}</a>}
    </div>
  </section>;
}
