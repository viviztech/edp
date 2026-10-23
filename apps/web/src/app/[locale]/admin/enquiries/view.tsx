"use client";
import { useEffect, useRef, useState } from "react";
import { enquiryWords, type Enquiry, type EnquiryList } from "../../../../lib/enquiry-content";
import "../../../../components/enquiries.css";

class RequestError extends Error { constructor(public status: number) { super(); } }
export default function EnquiryInbox({ org, locale, permissions }: { org: string; locale: "en" | "ta"; permissions: string[] }) {
  const t = enquiryWords[locale], base = `/api/enquiries/organizations/${org}/enquiries`;
  const [items, setItems] = useState<Enquiry[]>([]), [cursor, setCursor] = useState<string | null>(null);
  const [filter, setFilter] = useState("new"), [selected, setSelected] = useState<Enquiry | null>(null);
  const [busy, setBusy] = useState(false), [message, setMessage] = useState(""), [stale, setStale] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const selectedId = selected?.id;
  const queueUrl = `${base}/queue?limit=25${filter ? `&status=${filter}` : ""}`;
  async function api(path: string, data?: unknown) {
    const headers: Record<string, string> = {};
    if (data) {
      const csrf = await fetch("/api/session/csrf", { cache: "no-store" }); if (!csrf.ok) throw new RequestError(csrf.status);
      headers["x-csrf-token"] = (await csrf.json()).csrf_token; headers["Content-Type"] = "application/json";
    }
    const response = await fetch(path, { cache: "no-store", ...(data ? { method: "POST", body: JSON.stringify(data) } : {}), headers });
    if (!response.ok) throw new RequestError(response.status);
    return response.json();
  }
  useEffect(() => {
    let active = true;
    fetch(queueUrl, { cache: "no-store" }).then(async response => {
      if (!response.ok) throw new Error(); return response.json() as Promise<EnquiryList>;
    }).then(data => { if (active) { setItems(data.items); setCursor(data.next_cursor); } })
      .catch(() => { if (active) setMessage(t.staffError); });
    return () => { active = false; };
  }, [queueUrl, t.staffError]);
  useEffect(() => { if (selectedId) heading.current?.focus(); }, [selectedId]);
  async function run(work: () => Promise<void>) {
    setBusy(true); setMessage(""); try { await work(); }
    catch (error) { setMessage(error instanceof RequestError && error.status === 409 ? t.conflict : t.staffError); }
    finally { setBusy(false); }
  }
  async function load(more = false) {
    const data: EnquiryList = await api(queueUrl + (more && cursor ? `&cursor=${cursor}` : ""));
    setItems(old => more ? [...old, ...data.items] : data.items); setCursor(data.next_cursor);
  }
  function syncRecord(value: Enquiry) {
    setSelected(value);
    setItems(old => old.map(item => item.id === value.id ? value : item).filter(item => !filter || item.status === filter));
  }
  async function choose(id: string) {
    setSelected(null); setStale(false);
    const value: Enquiry = await api(`${base}/${id}`); syncRecord(value);
  }
  async function refreshDetail() {
    if (!selected) return;
    setStale(true); const value: Enquiry = await api(`${base}/${selected.id}`);
    syncRecord(value); setStale(false); setMessage(t.refreshed);
  }
  async function change(status: "reviewed" | "closed") {
    if (!selected || stale) return;
    setStale(true);
    try {
      const value: Enquiry = await api(`${base}/${selected.id}/status`, { expected_version: selected.version, status });
      syncRecord(value);
      setStale(false); setMessage(t.saved);
    } catch (error) {
      setMessage(error instanceof RequestError && error.status === 409 ? t.conflict : t.uncertain);
    }
  }
  return <div><p role="status" aria-live="polite">{busy ? t.loading : message}</p>
    <div className="enquiry-workspace" aria-busy={busy}>
      <aside aria-label={t.queue}><label>{t.status}<select value={filter} disabled={busy} onChange={event => { setFilter(event.target.value); setItems([]); setCursor(null); setMessage(""); }}>
        <option value="">{t.all}</option>{(["new", "reviewed", "closed"] as const).map(value => <option key={value} value={value}>{t[value]}</option>)}
      </select></label><button disabled={busy} onClick={() => run(() => load())}>{t.refresh}</button>
        {!items.length && <p>{t.empty}</p>}
        <ul>{items.map(item => <li key={item.id}><button disabled={busy} aria-pressed={selected?.id === item.id} onClick={() => run(() => choose(item.id))}>{item.name}<small>{t[item.status]}</small></button></li>)}</ul>
        {cursor && <button disabled={busy} onClick={() => run(() => load(true))}>{t.more}</button>}
      </aside>
      <section className="enquiry-detail" aria-label={t.details}>
        {selected ? <><h2 ref={heading} tabIndex={-1}>{selected.name}</h2>
          <dl><dt>{t.email}</dt><dd>{selected.email}</dd>{selected.phone && <><dt>{t.phone}</dt><dd>{selected.phone}</dd></>}
            <dt>{t.status}</dt><dd>{t[selected.status]} / v{selected.version}</dd>
            <dt>{t.received}</dt><dd><time dateTime={selected.created_at}>{new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Kolkata" }).format(new Date(selected.created_at))}</time></dd>
            <dt>{t.consentVersion}</dt><dd>{selected.consent_version}</dd></dl>
          <h3>{t.message}</h3><p className="enquiry-message">{selected.message}</p>
          <div className="actions"><button disabled={busy} onClick={() => run(refreshDetail)}>{t.refresh}</button>
            {permissions.includes("enquiry.manage") && selected.status !== "closed" && <button disabled={busy || stale} onClick={() => run(() => change(selected.status === "new" ? "reviewed" : "closed"))}>{selected.status === "new" ? t.markReviewed : t.close}</button>}
          </div>
        </> : <p>{t.choose}</p>}
      </section>
    </div>
  </div>;
}
