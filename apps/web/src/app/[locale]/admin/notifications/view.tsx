"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import type { components } from "../../../../lib/api-contracts";
import { notificationMessages, type NotificationLocale } from "../../../../lib/notification-messages";

type Item = components["schemas"]["NotificationView"];
type Preference = components["schemas"]["PreferenceView"];
type Page = components["schemas"]["NotificationList"];

export default function NotificationWorkspace({ org, locale }: { org: string; locale: NotificationLocale }) {
  const text = notificationMessages[locale];
  const root = `/api/notifications/organizations/${org}`;
  const [items, setItems] = useState<Item[]>([]);
  const [preference, setPreference] = useState<Preference | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const api = useCallback(async <T,>(path: string, method = "GET", data?: unknown): Promise<T> => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (method !== "GET") {
      const response = await fetch("/api/session/csrf", { cache: "no-store" });
      if (!response.ok) throw new Error(text.error);
      headers["x-csrf-token"] = (await response.json()).csrf_token;
    }
    const response = await fetch(path, {
      method, headers, body: data === undefined ? undefined : JSON.stringify(data), cache: "no-store",
    });
    if (!response.ok) throw new Error(response.status === 409 ? text.conflict : text.error);
    return response.json();
  }, [text.conflict, text.error]);

  const load = useCallback(async () => {
    const [page, pref] = await Promise.all([api<Page>(`${root}/mine`), api<Preference>(`${root}/preference`)]);
    setItems(page.items); setCursor(page.next_cursor ?? null); setPreference(pref);
  }, [api, root]);

  useEffect(() => {
    let active = true;
    Promise.all([api<Page>(`${root}/mine`), api<Preference>(`${root}/preference`)]).then(([page, pref]) => {
      if (!active) return;
      setItems(page.items); setCursor(page.next_cursor ?? null); setPreference(pref);
    }).catch(() => { if (active) setMessage(text.error); });
    return () => { active = false; };
  }, [api, root, text.error]);

  async function run(work: () => Promise<void>, success: string) {
    setBusy(true); setMessage("");
    try { await work(); setMessage(success); }
    catch (error) { setMessage(error instanceof Error ? error.message : text.error); }
    finally { setBusy(false); }
  }

  return <div className="notice-workspace" aria-busy={busy}>
    <p role="status" className="notice-message">{busy ? text.loading : message}</p>
    <section className="notice-preference" aria-label={text.preference}>
      <div><p className="eyebrow">{text.preference}</p><strong>{preference ? (preference.enabled ? text.enabled : text.disabled) : text.loading}</strong></div>
      {preference ? <button disabled={busy} onClick={() => run(async () => {
        const updated = await api<Preference>(`${root}/preference`, "POST", {
          enabled: !preference.enabled, expected_version: preference.version,
        });
        setPreference(updated);
      }, text.updated)}>{preference.enabled ? text.disable : text.enable}</button> : null}
    </section>
    <section className="notice-inbox" aria-label={text.workspace}>
      <div className="notice-section-head"><h2>{text.workspace}</h2><button disabled={busy} onClick={() => run(load, "")}>{text.refresh}</button></div>
      {items.length === 0 ? <p className="notice-empty">{text.empty}</p> : <ol>{items.map((item) =>
        <li key={item.id} className={item.read_at ? "notice-read" : "notice-unread"}>
          <div><span className="notice-indicator" aria-hidden="true" /><strong>{text.leadAssigned}</strong><time dateTime={item.created_at}>{new Date(item.created_at).toLocaleString(locale)}</time></div>
          <span className="notice-state">{item.read_at ? text.read : text.unread}</span>
          <div className="notice-actions"><Link href={`/${locale}/admin/crm?organization=${org}`}>{text.openCrm}</Link>
            {!item.read_at ? <button disabled={busy} onClick={() => run(async () => {
              const updated = await api<Item>(`${root}/${item.id}/read`, "POST", { expected_version: item.version });
              setItems((current) => current.map((entry) => entry.id === updated.id ? updated : entry));
            }, text.marked)}>{text.markRead}</button> : null}
          </div>
        </li>
      )}</ol>}
      {cursor ? <button disabled={busy} onClick={() => run(async () => {
        const page = await api<Page>(`${root}/mine?cursor=${cursor}`);
        setItems((current) => [...current, ...page.items]); setCursor(page.next_cursor ?? null);
      }, "")}>{text.more}</button> : null}
    </section>
  </div>;
}
