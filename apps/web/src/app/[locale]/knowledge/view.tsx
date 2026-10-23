"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { components } from "../../../lib/api-contracts";
import { FundingHistory, nextStatuses, ResourceCard, ResourceFilters, statusLabel, words,
  type FundingCase, type Locale, type Mine, type Resource } from "./content";

type Batch = components["schemas"]["KnowledgeList"];
export async function knowledgeMutation(url: string, body: unknown, method = "POST") {
  const csrf = await fetch("/api/session/csrf", { cache: "no-store" });
  if (!csrf.ok) throw new Error("csrf_failed");
  const { csrf_token } = await csrf.json() as { csrf_token: string };
  return fetch(url, { method, headers: { "Content-Type": "application/json", "x-csrf-token": csrf_token },
    ...(method === "DELETE" ? {} : { body: JSON.stringify(body) }) });
}

function CaseEditor({ item, locale, disabled, change }: { item: FundingCase; locale: Locale; disabled: boolean;
  change: (item: FundingCase, status: FundingCase["status"], reason: string) => Promise<boolean> }) {
  const t = words[locale]; const options = nextStatuses[item.status];
  const [reason, setReason] = useState(""); const [next, setNext] = useState(options[0] ?? item.status);
  return <article className="program-panel" aria-label={item.item_title}><h3>{item.item_title}</h3>
    <p>{t.status}: <strong>{statusLabel(item.status, locale)}</strong></p>
    {options.length ? <form onSubmit={(event) => { event.preventDefault();
      void change(item, options.includes(next) ? next : options[0], reason).then((saved) => { if (saved) setReason(""); });
    }}><label>{t.next}<select name="status" value={options.includes(next) ? next : options[0]} disabled={disabled}
      onChange={(event) => setNext(event.target.value as FundingCase["status"])}>
      {options.map((status) => <option key={status} value={status}>{statusLabel(status, locale)}</option>)}
    </select></label><label>{t.reason}<textarea required maxLength={500} disabled={disabled} value={reason}
      onChange={(event) => setReason(event.target.value)} /></label>
      <button disabled={disabled || !reason.trim()}>{t.progress}</button></form> : <p>{t.terminal}</p>}
    <FundingHistory item={item} locale={locale} /></article>;
}

export default function KnowledgeWorkspace({ org, locale }: { org: string; locale: Locale }) {
  const t = words[locale]; const base = `/api/knowledge/organizations/${org}`;
  const [items, setItems] = useState<Resource[]>([]); const [cursor, setCursor] = useState<string | null>(null);
  const [mine, setMine] = useState<Mine | null>(null); const [query, setQuery] = useState(`locale=${locale}&limit=25`);
  const [loading, setLoading] = useState(true); const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(""); const [failed, setFailed] = useState(false);
  const [needsRefresh, setNeedsRefresh] = useState(false);
  const request = useRef(0); const mounted = useRef(true);
  const mutationLock = useRef(false);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; request.current += 1; }; }, []);
  const load = useCallback((search: string, append = false, includeMine = false) => {
    const generation = ++request.current;
    return Promise.all([fetch(`${base}/catalog?${search}`, { cache: "no-store" }), includeMine ? fetch(`${base}/mine`, { cache: "no-store" }) : null]).then(async ([catalog, own]) => {
      if (!catalog.ok || (own && !own.ok)) throw new Error(catalog.status === 403 || own?.status === 403 ? "access" : "load");
      const [batch, data] = await Promise.all([catalog.json() as Promise<Batch>, own ? own.json() as Promise<Mine> : null]);
      if (mounted.current && generation === request.current) {
        setFailed(false); setMessage("");
        setItems((old) => append ? [...old, ...batch.items.filter((item) => !old.some((previous) => previous.id === item.id))] : batch.items);
        setCursor(batch.next_cursor); if (data) setMine(data);
      }
    }).catch((error: unknown) => { if (mounted.current && generation === request.current) { setFailed(true); setMessage(error instanceof Error && error.message === "access" ? t.access : t.error); } })
      .finally(() => { if (mounted.current && generation === request.current) setLoading(false); });
  }, [base, t.access, t.error]);
  useEffect(() => { void load(`locale=${locale}&limit=25`, false, true); }, [load, locale]);
  function startLoad(search: string, append = false, includeMine = false) {
    setLoading(true); setMessage(""); setFailed(false); void load(search, append, includeMine);
  }
  async function mutate(path: string, body: unknown, method?: string) {
    if (needsRefresh && path.endsWith("/status")) return false;
    if (mutationLock.current) return false; mutationLock.current = true;
    setBusy(true); setMessage("");
    try {
      const response = await knowledgeMutation(`${base}/${path}`, body, method);
      if (!response.ok) { setMessage(response.status === 409 ? t.conflict : response.status === 403 ? t.access : t.error); setNeedsRefresh(response.status === 409 || path.endsWith("/status")); return false; }
      if (method === "DELETE") setMine((old) => old && ({ ...old, saved_items: old.saved_items.filter((item) => !path.endsWith(item.item_id)) }));
      else {
        const result = await response.json();
        setMine((old) => {
          if (!old) return old;
          if (path.startsWith("saved/")) { const item = result as Mine["saved_items"][number];
            return { ...old, saved_items: [...old.saved_items.filter((entry) => entry.item_id !== item.item_id), item] }; }
          if (path.startsWith("interests/")) { const item = result as Mine["interests"][number];
            return { ...old, interests: [...old.interests.filter((entry) => entry.id !== item.id), item] }; }
          const item = result as FundingCase;
          return { ...old, funding_cases: old.funding_cases.some((entry) => entry.id === item.id)
            ? old.funding_cases.map((entry) => entry.id === item.id ? item : entry) : [...old.funding_cases, item] };
        });
      }
      setNeedsRefresh(false); setMessage(t.done); return true;
    } catch { setMessage(t.error); if (path.endsWith("/status")) setNeedsRefresh(true); return false; } finally { mutationLock.current = false; setBusy(false); }
  }
  async function refreshProgress() {
    if (mutationLock.current) return; mutationLock.current = true; setBusy(true); setMessage("");
    try {
      const known = new Set(mine?.funding_cases.map((item) => item.id) ?? []); const latest = new Map<string, FundingCase>();
      let cursor: string | null = null;
      do {
        const response = await fetch(`${base}/mine?limit=100${cursor ? `&case_cursor=${cursor}` : ""}`, { cache: "no-store" });
        if (!response.ok) throw new Error(); const batch = await response.json() as Mine;
        for (const item of batch.funding_cases) { latest.set(item.id, item); known.delete(item.id); }
        cursor = batch.next_case_cursor;
      } while (cursor && known.size);
      if (known.size) throw new Error("case_unavailable");
      setMine((old) => old && ({ ...old, funding_cases: old.funding_cases.map((item) => latest.get(item.id) ?? item) }));
      setNeedsRefresh(false); setMessage(t.refreshed);
    } catch { setMessage(t.error); } finally { mutationLock.current = false; setBusy(false); }
  }
  async function moreMine(which: "saved" | "interest" | "case") {
    const cursor = which === "saved" ? mine?.next_saved_cursor : which === "interest" ? mine?.next_interest_cursor : mine?.next_case_cursor;
    if (!cursor || mutationLock.current) return; mutationLock.current = true; setBusy(true); setMessage("");
    try {
      const response = await fetch(`${base}/mine?${which}_cursor=${cursor}&limit=25`, { cache: "no-store" });
      if (!response.ok) throw new Error(); const batch = await response.json() as Mine;
      setMine((old) => old && ({ ...old,
        ...(which === "saved" ? { saved_items: [...old.saved_items, ...batch.saved_items.filter((item) => !old.saved_items.some((previous) => previous.item_id === item.item_id))], next_saved_cursor: batch.next_saved_cursor } : {}),
        ...(which === "interest" ? { interests: [...old.interests, ...batch.interests.filter((item) => !old.interests.some((previous) => previous.id === item.id))], next_interest_cursor: batch.next_interest_cursor } : {}),
        ...(which === "case" ? { funding_cases: [...old.funding_cases, ...batch.funding_cases.filter((item) => !old.funding_cases.some((previous) => previous.id === item.id))], next_case_cursor: batch.next_case_cursor } : {}),
      }));
    } catch { setMessage(t.error); } finally { mutationLock.current = false; setBusy(false); }
  }
  const actions = (item: Resource) => <p>
    <button disabled={busy || loading} onClick={() => void mutate(`saved/${item.id}`, {}, mine?.saved_items.some((saved) => saved.item_id === item.id) ? "DELETE" : "POST")}>
      {mine?.saved_items.some((saved) => saved.item_id === item.id) ? t.unsave : t.save}</button>{" "}
    {item.kind === "opportunity" && <button disabled={busy || loading || item.availability === "closed" || mine?.interests.some((interest) => interest.item_id === item.id)}
      onClick={() => void mutate(`interests/${item.id}`, {})}>{mine?.interests.some((interest) => interest.item_id === item.id) ? t.interested : t.interest}</button>}
    {item.kind === "funding" && <button disabled={busy || loading || item.availability === "closed" || mine?.funding_cases.some((funding) => funding.item_id === item.id)}
      onClick={() => void mutate("funding-cases", { item_id: item.id })}>{t.start}</button>}
  </p>;
  return <><header className="program-heading"><div><p className="eyebrow">K01</p><h1>{t.title}</h1><p>{t.intro}</p></div></header>
    <ResourceFilters locale={locale} disabled={busy || loading} onSubmit={(event) => {
      event.preventDefault(); const filters = new URLSearchParams({ locale, limit: "25" });
      for (const [key, value] of new FormData(event.currentTarget)) if (String(value).trim()) filters.set(key, String(value).trim());
      setQuery(filters.toString()); startLoad(filters.toString());
    }} /><p role="status">{loading ? t.loading : message}</p>
    {failed && <button disabled={loading || busy} onClick={() => startLoad(query, false, !mine)}>{t.retry}</button>}
    {needsRefresh && <button disabled={loading || busy} onClick={() => void refreshProgress()}>{t.refreshProgress}</button>}
    {!loading && !failed && !items.length && <p>{t.empty}</p>}
    <section aria-label={t.title}>{items.map((item) => <ResourceCard key={item.id} item={item} locale={locale}>{actions(item)}</ResourceCard>)}</section>
    {cursor && <button disabled={loading || busy} onClick={() => startLoad(`${query}&cursor=${cursor}`, true)}>{t.more}</button>}
    {mine && <><section className="program-panel"><h2>{t.saved}</h2>
      {!mine.saved_items.length && <p>{t.noSaved}</p>}{mine.saved_items.map((saved) => saved.item ? <ResourceCard key={saved.item_id} item={saved.item} locale={locale}>{actions(saved.item)}</ResourceCard>
        : <div key={saved.item_id}><p>{t.unavailable}</p><button disabled={busy || loading} onClick={() => void mutate(`saved/${saved.item_id}`, {}, "DELETE")}>{t.unsave}</button></div>)}
      {mine.next_saved_cursor && <button disabled={busy || loading} onClick={() => void moreMine("saved")}>{t.more}</button>}
    </section><section className="program-panel"><h2>{t.interests}</h2>{mine.interests.length ? <ul>{mine.interests.map((interest) => <li key={interest.id}>{interest.item_title} · {new Date(interest.created_at).toLocaleDateString(locale)}</li>)}</ul> : <p>{t.noInterest}</p>}
      {mine.next_interest_cursor && <button disabled={busy || loading} onClick={() => void moreMine("interest")}>{t.more}</button>}</section>
    <section aria-label={t.cases}><h2>{t.cases}</h2><p>{t.reported}</p>{!mine.funding_cases.length && <p>{t.noCases}</p>}
      {mine.funding_cases.map((item) => <CaseEditor key={item.id} item={item} locale={locale} disabled={busy || loading || needsRefresh}
        change={(funding, status, reason) => mutate(`funding-cases/${funding.id}/status`, { expected_version: funding.version, status, reason })} />)}
      {mine.next_case_cursor && <button disabled={busy || loading} onClick={() => void moreMine("case")}>{t.more}</button>}
    </section></>}
  </>;
}
