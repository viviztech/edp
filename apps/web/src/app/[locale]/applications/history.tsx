"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { components } from "../../../lib/api-contracts";
import { applicationMessages } from "../../../lib/application-messages";
import { applicationHref } from "../../../lib/intake-context";

type HistoryList = components["schemas"]["ApplicationHistoryList"];
type HistoryItem = HistoryList["items"][number];

async function readHistory(cursor?: string, signal?: AbortSignal): Promise<HistoryList> {
  const search = new URLSearchParams({ limit: "20" });
  if (cursor) search.set("cursor", cursor);
  const response = await fetch(`/api/applications/mine?${search}`, { cache: "no-store", signal });
  if (!response.ok) throw new Error("history_unavailable");
  const result: HistoryList = await response.json();
  if (!Array.isArray(result.items) || !(result.next_cursor === null || typeof result.next_cursor === "string")) throw new Error("invalid_history");
  return result;
}

export default function ApplicationHistory({ locale, refreshKey, currentId, canNavigate, navigationBlocked = false }: {
  locale: "en" | "ta"; refreshKey: number; currentId?: string; canNavigate: () => boolean; navigationBlocked?: boolean;
}) {
  const t = applicationMessages[locale];
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState<"initial" | "more" | null>(null);
  const [retry, setRetry] = useState(0);
  const [settled, setSettled] = useState({ refreshKey, retry: 0 });
  const replacing = settled.refreshKey !== refreshKey || settled.retry !== retry;
  const isLoading = loading || replacing;
  const generation = useRef({ value: 0 });
  const morePending = useRef<number | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const counter = generation.current;
    const version = ++counter.value;
    readHistory(undefined, controller.signal).then((result) => {
      if (controller.signal.aborted || version !== generation.current.value) return;
      setItems(result.items); setCursor(result.next_cursor); setFailed(null);
    }).catch(() => {
      if (!controller.signal.aborted && version === generation.current.value) setFailed("initial");
    }).finally(() => {
      if (!controller.signal.aborted && version === generation.current.value) {
        setLoading(false); setSettled({ refreshKey, retry });
      }
    });
    return () => { controller.abort(); counter.value++; };
  }, [refreshKey, retry]);

  async function more() {
    if (!cursor || isLoading || failed === "initial" || morePending.current === generation.current.value) return;
    const version = generation.current.value;
    morePending.current = version; setLoading(true); setFailed(null);
    try {
      const result = await readHistory(cursor);
      if (version !== generation.current.value) return;
      setItems((current) => [...current, ...result.items.filter((item) => !current.some((existing) => existing.id === item.id))]);
      setCursor(result.next_cursor);
    } catch { if (version === generation.current.value) setFailed("more"); }
    finally {
      if (morePending.current === version) morePending.current = null;
      if (version === generation.current.value) setLoading(false);
    }
  }

  return <section className="application-saved" aria-label={t.savedApplications} aria-busy={isLoading}>
    <h2>{t.savedApplications}</h2>
    {isLoading && <p role="status">{t.loadingHistory}</p>}
    {failed && !replacing && <div><p role="alert">{t.historyError}</p><button type="button" disabled={isLoading} onClick={() => {
      if (failed === "more") void more();
      else { setLoading(true); setRetry((value) => value + 1); }
    }}>{t.retry}</button></div>}
    {!isLoading && !failed && items.length === 0 && <p>{t.historyEmpty}</p>}
    <ul>{items.map((item) => <li key={item.id}>
      <strong>{item.organization_name}</strong>
      <span>{locale === "ta" ? item.cycle_name_ta : item.cycle_name_en}</span>
      <span>{t.status}: {t.states[item.state]}</span>
      {item.application_number && <span>{t.receipt}: {item.application_number}</span>}
      <time dateTime={item.updated_at}>{t.updated}: {new Date(item.updated_at).toLocaleString(locale)}</time>
      {item.cycle_id ? <Link href={applicationHref(locale, { organization: item.organization_id, cycle: item.cycle_id })}
        aria-current={item.id === currentId ? "page" : undefined}
        aria-disabled={navigationBlocked} tabIndex={navigationBlocked ? -1 : undefined}
        onClick={(event) => { if (navigationBlocked || !canNavigate()) event.preventDefault(); }}>
        {item.state === "draft" ? t.continueDraft : t.view}
      </Link> : <p>{t.legacy}</p>}
    </li>)}</ul>
    {cursor && failed !== "initial" && <button type="button" disabled={isLoading} onClick={() => void more()}>{t.more}</button>}
  </section>;
}
