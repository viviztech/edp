"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import type { Locale } from "../../../lib/messages";
import { updateMessages } from "./content";
import type { NoticeList, NoticePreference, ParticipantNotice } from "./types";

class RequestFailure extends Error { constructor(public status: number) { super("request_failed"); } }
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const date = (value: unknown): value is string => typeof value === "string" && Number.isFinite(Date.parse(value));
function notice(value: ParticipantNotice): ParticipantNotice {
  if (!value || !uuid.test(value.id) || !uuid.test(value.enrollment_id) || value.topic !== "enrollment_created"
    || value.template_version !== "enrollment-created-v1" || value.action_kind !== "schedule"
    || !date(value.created_at) || !date(value.expires_at) || value.read_at !== null && !date(value.read_at)
    || !Number.isSafeInteger(value.version) || value.version < 1) throw new Error();
  return value;
}
function preference(value: NoticePreference): NoticePreference {
  if (!value || typeof value.enabled !== "boolean" || value.topic !== "enrollment_created" || !Number.isSafeInteger(value.version) || value.version < 0) throw new Error();
  return value;
}
async function readList(root: string, cursor: string | null): Promise<NoticeList> {
  const query = new URLSearchParams({ limit: "25", ...(cursor ? { cursor } : {}) });
  const response = await fetch(`${root}/mine?${query}`, { cache: "no-store" });
  if (!response.ok) throw new RequestFailure(response.status);
  const value: NoticeList = await response.json();
  if (!value || !Array.isArray(value.items) || value.items.length > 25 || value.next_cursor !== null && !uuid.test(value.next_cursor)) throw new Error();
  return { items: value.items.map(notice), next_cursor: value.next_cursor };
}
async function readPreference(root: string) {
  const response = await fetch(`${root}/preference`, { cache: "no-store" });
  if (!response.ok) throw new RequestFailure(response.status);
  return preference(await response.json());
}
async function command(path: string, body: object) {
  const csrf = await fetch("/api/session/csrf", { cache: "no-store" });
  if (!csrf.ok) throw new RequestFailure(csrf.status);
  const token: unknown = (await csrf.json()).csrf_token;
  if (typeof token !== "string" || !token || token.length > 128) throw new Error();
  const response = await fetch(path, { method: "POST", cache: "no-store", headers: { "Content-Type": "application/json", "x-csrf-token": token }, body: JSON.stringify(body) });
  if (!response.ok) throw new RequestFailure(response.status);
  return response.json();
}

export default function Updates({ org, locale }: { org: string; locale: Locale }) {
  const t = updateMessages[locale], root = `/api/participant-notifications/organizations/${org}`;
  const [items, setItems] = useState<ParticipantNotice[]>([]), [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true), [loaded, setLoaded] = useState(false), [listMessage, setListMessage] = useState("");
  const [pref, setPref] = useState<NoticePreference | null>(null), [selected, setSelected] = useState<boolean | null>(null);
  const [prefLoading, setPrefLoading] = useState(true), [prefMessage, setPrefMessage] = useState("");
  const [needsCheck, setNeedsCheck] = useState(false), [readChecks, setReadChecks] = useState<string[]>([]);
  const [busy, setBusy] = useState(false), [accessError, setAccessError] = useState("");
  const [now, setNow] = useState(() => Date.now());
  const mounted = useRef(true), operation = useRef(false), listLock = useRef(false), prefLock = useRef(false), epoch = useRef(0);
  const draft = useRef<boolean | null>(null);
  const denied = useCallback((error: unknown) => {
    if (!(error instanceof RequestFailure) || ![401, 403, 404].includes(error.status)) return false;
    epoch.current++; setItems([]); setCursor(null); setPref(null); setSelected(null); draft.current = null;
    setAccessError(error.status === 401 ? t.session : t.access);
    return true;
  }, [t.access, t.session]);
  const load = useCallback(async (continuation: string | null = null) => {
    if (listLock.current) return;
    const generation = epoch.current;
    listLock.current = true; setLoading(true); setListMessage("");
    try {
      const value = await readList(root, continuation);
      if (!mounted.current || generation !== epoch.current) return;
      setItems(previous => continuation ? [...previous, ...value.items.filter(item => !previous.some(old => old.id === item.id))] : value.items);
      setCursor(value.next_cursor); setLoaded(true); setNow(Date.now());
      if (!continuation) setReadChecks([]);
    } catch (error) {
      if (mounted.current && generation === epoch.current && !denied(error)) setListMessage(t.error);
    } finally { if (generation === epoch.current) { listLock.current = false; if (mounted.current) setLoading(false); } }
  }, [denied, root, t.error]);
  const loadPreference = useCallback(async () => {
    if (prefLock.current) return;
    const generation = epoch.current;
    prefLock.current = true; setPrefLoading(true); setPrefMessage("");
    try {
      const value = await readPreference(root);
      if (!mounted.current || generation !== epoch.current) return;
      setPref(value); setNeedsCheck(false);
      if (draft.current === null) { draft.current = value.enabled; setSelected(value.enabled); }
    } catch (error) {
      if (mounted.current && generation === epoch.current && !denied(error)) { setNeedsCheck(true); setPrefMessage(t.preferenceError); }
    } finally { if (generation === epoch.current) { prefLock.current = false; if (mounted.current) setPrefLoading(false); } }
  }, [denied, root, t.preferenceError]);
  useEffect(() => {
    mounted.current = true;
    const generation = epoch.current;
    listLock.current = true; prefLock.current = true;
    readList(root, null).then(value => {
      if (!mounted.current || generation !== epoch.current) return;
      setItems(value.items); setCursor(value.next_cursor); setLoaded(true); setNow(Date.now());
    }).catch(error => {
      if (mounted.current && generation === epoch.current && !denied(error)) setListMessage(t.error);
    }).finally(() => {
      if (mounted.current && generation === epoch.current) { listLock.current = false; setLoading(false); }
    });
    readPreference(root).then(value => {
      if (!mounted.current || generation !== epoch.current) return;
      setPref(value); draft.current = value.enabled; setSelected(value.enabled);
    }).catch(error => {
      if (mounted.current && generation === epoch.current && !denied(error)) { setNeedsCheck(true); setPrefMessage(t.preferenceError); }
    }).finally(() => {
      if (mounted.current && generation === epoch.current) { prefLock.current = false; setPrefLoading(false); }
    });
    return () => { mounted.current = false; epoch.current = generation + 1; listLock.current = false; prefLock.current = false; };
  }, [denied, root, t.error, t.preferenceError]);
  const nextExpiry = Math.min(...items.map(item => Date.parse(item.expires_at)).filter(value => value > now));
  useEffect(() => {
    if (!Number.isFinite(nextExpiry)) return;
    const timer = window.setTimeout(() => setNow(Date.now()), Math.min(Math.max(1, nextExpiry - Date.now()), 2147483647));
    return () => window.clearTimeout(timer);
  }, [nextExpiry, now]);

  async function savePreference(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (operation.current || !pref || selected === null || needsCheck || prefLoading || accessError) return;
    operation.current = true; setBusy(true); setPrefMessage("");
    const generation = epoch.current;
    try {
      const value = preference(await command(`${root}/preference`, { enabled: selected, expected_version: pref.version }));
      if (!mounted.current || generation !== epoch.current) return;
      setPref(value); draft.current = value.enabled; setSelected(value.enabled); setPrefMessage(t.saved);
    } catch (error) {
      if (!mounted.current || generation !== epoch.current || denied(error)) return;
      setNeedsCheck(true); setPrefMessage(error instanceof RequestFailure && error.status === 409 ? t.conflict : t.preferenceCheck);
    } finally { operation.current = false; if (mounted.current) setBusy(false); }
  }
  async function markRead(item: ParticipantNotice) {
    if (operation.current || loading || readChecks.includes(item.id) || accessError) return;
    operation.current = true; setBusy(true); setListMessage("");
    const generation = epoch.current;
    try {
      const value = notice(await command(`${root}/${item.id}/read`, { expected_version: item.version }));
      if (value.id !== item.id || !value.read_at) throw new Error();
      if (!mounted.current || generation !== epoch.current) return;
      setItems(previous => previous.map(old => old.id === item.id ? value : old)); setListMessage(t.readSaved);
    } catch (error) {
      if (!mounted.current || generation !== epoch.current || denied(error)) return;
      setReadChecks(previous => [...previous, item.id]); setListMessage(t.readCheck);
    } finally { operation.current = false; if (mounted.current) setBusy(false); }
  }
  const visible = items.filter(item => Date.parse(item.expires_at) > now);
  return <>
    <header className="updates-heading"><p className="eyebrow">{t.notices}</p><h1>{t.title}</h1><p>{t.intro}</p></header>
    {accessError ? <><p role="alert">{accessError}</p><Link href={`/${locale}/account`}>{t.back}</Link></> : <div className="updates-grid">
      <section className="updates-inbox" aria-label={t.notices} aria-busy={loading || busy}>
        <h2>{t.notices}</h2><p className="updates-status" role="status">{loading ? t.loading : listMessage}</p>
        {loaded && !loading && !visible.length && <p>{t.empty}</p>}
        <ul className="updates-list">{visible.map(item => <li key={item.id}>
          <article aria-label={t.enrollmentTitle}>
            <span className="updates-badge">{item.read_at ? t.read : t.unread}</span>
            <h3>{t.enrollmentTitle}</h3><p>{t.enrollmentBody}</p>
            <small>{t.received}<time dateTime={item.created_at}>{new Date(item.created_at).toLocaleString(locale)}</time></small>
            <small>{t.until}<time dateTime={item.expires_at}>{new Date(item.expires_at).toLocaleString(locale)}</time></small>
            <div className="actions"><Link href={`/${locale}/participant?${new URLSearchParams({ organization: org })}`}>{t.schedule}</Link>
              {!item.read_at && <button type="button" disabled={busy || loading || readChecks.includes(item.id)} onClick={() => void markRead(item)}>{t.markRead}</button>}
            </div>
          </article>
        </li>)}</ul>
        <div className="actions"><button type="button" disabled={busy || loading} onClick={() => void load()}>{t.refresh}</button>
          {cursor && <button type="button" disabled={busy || loading} onClick={() => void load(cursor)}>{t.more}</button>}
        </div>
      </section>
      <section className="updates-preferences" aria-label={t.preferences} aria-busy={prefLoading || busy}>
        <h2>{t.preferences}</h2><p>{t.preferenceHelp}</p>
        <p className="updates-status" role="status">{prefLoading ? t.preferenceLoading : prefMessage}</p>
        {pref && <p>{pref.enabled ? t.enabledNow : t.disabledNow}</p>}
        <form onSubmit={savePreference}>
          <label><input name="enabled" type="checkbox" checked={selected ?? false} disabled={busy || prefLoading || selected === null} onChange={event => { draft.current = event.target.checked; setSelected(event.target.checked); }} />{t.enabled}</label>
          {pref && selected !== pref.enabled && <p>{t.unsaved}</p>}
          <button type="submit" disabled={busy || prefLoading || !pref || needsCheck || selected === pref.enabled}>{busy ? t.working : t.save}</button>
          <button type="button" disabled={busy || prefLoading} onClick={() => void loadPreference()}>{t.checkPreference}</button>
        </form>
      </section>
    </div>}
  </>;
}
