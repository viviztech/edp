"use client";
import { useEffect, useState } from "react";
import type { components } from "../../../lib/api-contracts";
import { toolsCopy, type ToolsLocale } from "../../../lib/business-tools-copy";
import CardEditor from "./card";
import CatalogueEditor from "./catalogue";
import QuotesEditor from "./quotes";
import { Contacts, Tasks } from "./crm";
import { type Card, type Catalogue, type Contact, type History, type Item, type Page, Pager, type Quote, read, type Task } from "./client";
type Businesses = components["schemas"]["MyBusinesses"];
type Initial = { card: Card | null; catalogue: Catalogue; quotes: Page<Quote>; contacts: Page<Contact>; tasks: Page<Task> };

function Tools({ org, profile, locale }: { org: string; profile: string; locale: ToolsLocale }) {
  const base = `/api/business-tools/organizations/${org}/profiles/${profile}`;
  const t = toolsCopy[locale]; const [data, setData] = useState<Initial | null>(null);
  const [items, setItems] = useState<Item[]>([]); const [contacts, setContacts] = useState<Contact[]>([]);
  const [history, setHistory] = useState<Page<History> | null>(null); const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    Promise.all([read<Card | null>(`${base}/card`), read<Catalogue>(`${base}/catalogue`), read<Page<Quote>>(`${base}/quotes`), read<Page<Contact>>(`${base}/contacts`), read<Page<Task>>(`${base}/tasks`)])
      .then(([card, catalogue, quotes, contacts, tasks]) => { if (active) { setData({ card, catalogue, quotes, contacts, tasks }); setItems(catalogue.items); setContacts(contacts.items); } })
      .catch(() => { if (active) setError(t.unavailable); });
    return () => { active = false; };
  }, [base, t.unavailable, attempt]);
  async function loadHistory(offset = 0) { try { setHistory(await read<Page<History>>(`${base}/history?limit=25&offset=${offset}`)); setError(""); } catch { setError(t.unavailable); } }
  if (!data) return <><p role="status">{error || t.loading}</p>{error && <button type="button" onClick={() => setAttempt(n => n + 1)}>{t.refresh}</button>}</>;
  return <><p role="status">{error}</p><CardEditor base={base} locale={locale} initial={data.card} />
    <CatalogueEditor base={base} locale={locale} initial={data.catalogue} onItems={setItems} />
    <QuotesEditor base={base} locale={locale} initial={data.quotes} items={items} />
    <h2>{t.crm}</h2><Contacts base={base} locale={locale} initial={data.contacts} onContacts={setContacts} />
    <Tasks base={base} locale={locale} initial={data.tasks} contacts={contacts} />
    <section className="program-panel"><h2>{t.history}</h2><button type="button" onClick={() => void loadHistory()}>{t.refresh}</button>
      {history && <><ol>{history.items.map(h => <li key={h.id}>{Object.hasOwn(t.actions, h.action) ? t.actions[h.action as keyof typeof t.actions] : t.history} · v{h.version} · <time dateTime={h.created_at}>{new Intl.DateTimeFormat(locale === "ta" ? "ta-IN" : "en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(h.created_at))}</time></li>)}</ol>
        {!history.items.length && <p>{t.noHistory}</p>}<Pager offset={history.offset} count={history.items.length} busy={false} onChange={offset => void loadHistory(offset)} t={t} /></>}
    </section></>;
}

export default function BusinessToolsView({ org, locale }: { org: string; locale: ToolsLocale }) {
  const t = toolsCopy[locale]; const [entries, setEntries] = useState<Businesses["entries"] | null>(null);
  const [selected, setSelected] = useState(""); const [error, setError] = useState(""); const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    read<Businesses>(`/api/businesses/organizations/${org}/mine`).then(body => {
      if (active) { setEntries(body.entries.filter(e => e.profile)); setSelected(body.entries.find(e => e.profile)?.profile?.id ?? ""); setError(""); }
    }).catch(() => { if (active) setError(t.unavailable); });
    return () => { active = false; };
  }, [org, t.unavailable, attempt]);
  return <><header className="program-heading"><div><h1>{t.title}</h1><p>{t.intro}</p></div></header>
    {!entries && <p role="status">{error || t.loading}</p>}{error && <button type="button" onClick={() => setAttempt(i => i + 1)}>{t.refresh}</button>}
    {entries?.length === 0 && <a href={`/${locale}/businesses?organization=${org}`}>{t.setup}</a>}
    {!!entries?.length && <><label>{t.business}<select value={selected} onChange={event => {
      if (window.confirm(locale === "ta" ? "தொழிலை மாற்றவா? சேமிக்காத விவரங்கள் இழக்கப்படும்." : "Switch business? Unsaved input will be lost.")) setSelected(event.target.value);
    }}>{entries.map(e => <option key={e.enrollment_id} value={e.profile!.id}>{e.profile!.name}</option>)}</select></label>
      {selected && <Tools key={`${org}-${selected}-${locale}`} org={org} profile={selected} locale={locale} />}</>}
  </>;
}
