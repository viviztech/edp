"use client";

import { useCallback, useEffect, useState } from "react";
import type { components } from "../../../../lib/api-contracts";

type Failure = components["schemas"]["FailureView"];
type Page = components["schemas"]["FailureList"];
const copy = {
  en: {
    heading: "Delivery failures", description: "In-app notices that exhausted automatic retries.",
    empty: "No failed notices.", retry: "Retry", more: "Load more", refresh: "Refresh",
    error: "Could not load delivery failures.", conflict: "This notice changed. Refresh and try again.",
    done: "Retry queued.", reason: "Reason for retry",
    attempts: "attempts", pending: "Working...",
  },
  ta: {
    heading: "\u0bb5\u0bb4\u0b99\u0bcd\u0b95\u0bb2\u0bcd \u0ba4\u0bcb\u0bb2\u0bcd\u0bb5\u0bbf\u0b95\u0bb3\u0bcd",
    description: "\u0ba4\u0bbe\u0ba9\u0bbf\u0baf\u0b99\u0bcd\u0b95\u0bbf \u0bae\u0bc0\u0bb3\u0bcd\u0bae\u0bc1\u0baf\u0bb1\u0bcd\u0b9a\u0bbf \u0ba4\u0bcb\u0bb2\u0bcd\u0bb5\u0bbf\u0baf\u0b9f\u0bc8\u0ba8\u0bcd\u0ba4 \u0b85\u0bb1\u0bbf\u0bb5\u0bbf\u0baa\u0bcd\u0baa\u0bc1\u0b95\u0bb3\u0bcd.",
    empty: "\u0ba4\u0bcb\u0bb2\u0bcd\u0bb5\u0bbf\u0baf\u0b9f\u0bc8\u0ba8\u0bcd\u0ba4 \u0b85\u0bb1\u0bbf\u0bb5\u0bbf\u0baa\u0bcd\u0baa\u0bc1\u0b95\u0bb3\u0bcd \u0b87\u0bb2\u0bcd\u0bb2\u0bc8.",
    retry: "\u0bae\u0bc0\u0ba3\u0bcd\u0b9f\u0bc1\u0bae\u0bcd \u0bae\u0bc1\u0baf\u0bb1\u0bcd\u0b9a\u0bbf", more: "\u0bae\u0bc7\u0bb2\u0bc1\u0bae\u0bcd", refresh: "\u0baa\u0bc1\u0ba4\u0bc1\u0baa\u0bcd\u0baa\u0bbf",
    error: "\u0ba4\u0bcb\u0bb2\u0bcd\u0bb5\u0bbf\u0b95\u0bb3\u0bc8 \u0b8f\u0bb1\u0bcd\u0bb1 \u0bae\u0bc1\u0b9f\u0bbf\u0baf\u0bb5\u0bbf\u0bb2\u0bcd\u0bb2\u0bc8.",
    conflict: "\u0b85\u0bb1\u0bbf\u0bb5\u0bbf\u0baa\u0bcd\u0baa\u0bc1 \u0bae\u0bbe\u0bb1\u0bbf\u0baf\u0bc1\u0bb3\u0bcd\u0bb3\u0ba4\u0bc1.",
    done: "\u0bae\u0bc0\u0bb3\u0bcd\u0bae\u0bc1\u0baf\u0bb1\u0bcd\u0b9a\u0bbf \u0bb5\u0bb0\u0bbf\u0b9a\u0bc8\u0baf\u0bbf\u0bb2\u0bcd \u0b9a\u0bc7\u0bb0\u0bcd\u0b95\u0bcd\u0b95\u0baa\u0bcd\u0baa\u0b9f\u0bcd\u0b9f\u0ba4\u0bc1.",
    reason: "\u0bae\u0bc0\u0bb3\u0bcd\u0bae\u0bc1\u0baf\u0bb1\u0bcd\u0b9a\u0bbf\u0b95\u0bcd\u0b95\u0bbe\u0ba9 \u0b95\u0bbe\u0bb0\u0ba3\u0bae\u0bcd",
    attempts: "\u0bae\u0bc1\u0baf\u0bb1\u0bcd\u0b9a\u0bbf\u0b95\u0bb3\u0bcd", pending: "\u0b9a\u0bc6\u0baf\u0bb2\u0bcd\u0baa\u0b9f\u0bc1\u0b95\u0bbf\u0bb1\u0ba4\u0bc1...",
  },
} as const;

export default function NotificationOperations({ org, locale, canReplay }: { org: string; locale: "en" | "ta"; canReplay: boolean }) {
  const t = copy[locale];
  const root = `/api/notifications/organizations/${org}/operations`;
  const [items, setItems] = useState<Failure[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [message, setMessage] = useState("");
  const [reason, setReason] = useState("");
  const load = useCallback(async (after?: string) => {
    const response = await fetch(`${root}/failed${after ? `?cursor=${after}` : ""}`, { cache: "no-store" });
    if (!response.ok) throw new Error(t.error);
    const page: Page = await response.json();
    setItems((current) => after ? [...current, ...page.items] : page.items);
    setCursor(page.next_cursor ?? null);
    setLoaded(true);
  }, [root, t.error]);
  useEffect(() => {
    let active = true;
    fetch(`${root}/failed`, { cache: "no-store" })
      .then(async (response) => { if (!response.ok) throw new Error(t.error); return response.json() as Promise<Page>; })
      .then((page) => { if (active) { setItems(page.items); setCursor(page.next_cursor ?? null); setLoaded(true); } })
      .catch(() => { if (active) setMessage(t.error); });
    return () => { active = false; };
  }, [root, t.error]);
  async function run(task: () => Promise<void>) {
    setBusy(true); setMessage("");
    try { await task(); }
    catch (error) { setMessage(error instanceof Error ? error.message : t.error); }
    finally { setBusy(false); }
  }
  async function replay(item: Failure) {
    const tokenResponse = await fetch("/api/session/csrf", { cache: "no-store" });
    if (!tokenResponse.ok) throw new Error(t.error);
    const token = (await tokenResponse.json()).csrf_token;
    const response = await fetch(`${root}/${item.id}/replay`, {
      method: "POST", cache: "no-store",
      headers: { "Content-Type": "application/json", "x-csrf-token": token },
      body: JSON.stringify({ expected_version: item.version, reason: reason.trim() }),
    });
    if (!response.ok) throw new Error(response.status === 409 ? t.conflict : t.error);
    await load();
    setReason("");
    setMessage(t.done);
  }
  return <section className="notice-preference" aria-labelledby="notification-operations-heading" aria-busy={busy}>
    <div>
      <p className="eyebrow" id="notification-operations-heading">{t.heading}</p>
      <p>{t.description}</p>
      <p role="status">{busy ? t.pending : message}</p>
      {canReplay && items.length > 0 ? <label>{t.reason}<input value={reason} maxLength={500} onChange={(event) => setReason(event.target.value)} /></label> : null}
      {items.length === 0 ? (loaded ? <p>{t.empty}</p> : null) : <ul>{items.map((item) => <li key={item.id}>
        <strong>{item.topic === "followup_due" ? "CRM follow-up" : "Lead assignment"}</strong>
        {" - "}{item.attempt_count} {t.attempts} - {item.error_code}
        {canReplay ? <button type="button" disabled={busy || reason.trim().length < 8} onClick={() => void run(() => replay(item))}>{t.retry}</button> : null}
      </li>)}</ul>}
      {cursor ? <button type="button" disabled={busy} onClick={() => void run(() => load(cursor))}>{t.more}</button> : null}
      <button type="button" disabled={busy} onClick={() => void run(() => load())}>{t.refresh}</button>
    </div>
  </section>;
}
