"use client";
import { useState } from "react";
import { toolsCopy, type ToolsLocale } from "../../../lib/business-tools-copy";
import { CommandState, type Catalogue, type Item, type ItemFields, Pager, read, useCommand, useDirtyGuard } from "./client";
import { SavedReview } from "./card";
const empty: ItemFields = { kind: "product", name_en: "", name_ta: "", description_en: "", description_ta: "", available: true, price: null, currency: "INR" };
function fields(item: ItemFields): ItemFields { return { kind: item.kind, name_en: item.name_en, name_ta: item.name_ta, description_en: item.description_en, description_ta: item.description_ta, available: item.available, price: item.price, currency: item.currency }; }

export default function CatalogueEditor({ base, locale, initial, onItems }: { base: string; locale: ToolsLocale; initial: Catalogue; onItems: (items: Item[]) => void }) {
  const t = toolsCopy[locale]; const command = useCommand(t);
  const [data, setData] = useState(initial); const [editing, setEditing] = useState<Item | null>(null);
  const [draft, setDraft] = useState<ItemFields>(empty); const [loaded, setLoaded] = useState(false);
  const [latest, setLatest] = useState<Item | null>(null);
  const [error, setError] = useState(""); const [offset, setOffset] = useState(0);
  const dirty = JSON.stringify(draft) !== JSON.stringify(fields(editing ?? empty));
  useDirtyGuard(dirty || command.pending);
  async function load(next = offset) {
    try { const body = await read<Catalogue>(`${base}/catalogue?limit=25&offset=${next}`);
      const current = editing ? await read<Item>(`${base}/catalogue/items/${editing.id}`) : null;
      setLatest(current); setData(body); onItems(body.items); setOffset(next); setLoaded(true); setError(""); }
    catch { setError(t.unavailable); }
  }
  function select(item: Item | null) { setEditing(item); setDraft(fields(item ?? empty)); setLatest(null); setLoaded(false); }
  return <section className="program-panel"><h2>{t.catalogue}</h2><CommandState command={command} t={t} /><p role="status">{error}</p>
    <ul className="program-list">{data.items.map(item => <li key={item.id}><strong>{locale === "ta" ? item.name_ta : item.name_en}</strong> {item.price} {item.price && item.currency} · {item.available ? t.available : t.archived}
      <button type="button" disabled={command.blocked || dirty} onClick={() => select(item)}>{t.edit}</button></li>)}</ul>
    {!data.items.length && <p>{t.noItems}</p>}<Pager offset={offset} count={data.items.length} busy={command.blocked || dirty} onChange={value => void load(value)} t={t} />
    <button type="button" disabled={command.blocked || dirty} onClick={() => select(null)}>{t.newItem}</button>
    <form onSubmit={e => { e.preventDefault(); command.run<Item>(editing ? `${base}/catalogue/items/${editing.id}/update` : `${base}/catalogue/items`, { ...draft, ...(editing ? { expected_version: editing.version } : {}) }, item => {
      select(item); setData(old => ({ ...old, settings: old.settings ? { ...old.settings, published: false } : null, items: old.items.some(i => i.id === item.id) ? old.items.map(i => i.id === item.id ? item : i) : [item, ...old.items].slice(0, 25) })); void load();
    }); }}><fieldset disabled={command.busy || command.pending}><div className="tools-fields">
      <label>{t.kind}<select value={draft.kind} onChange={e => setDraft(old => ({ ...old, kind: e.target.value as ItemFields["kind"] }))}><option value="product">{t.product}</option><option value="service">{t.service}</option></select></label>
      {(["name_en", "name_ta", "description_en", "description_ta"] as const).map(key => <label key={key}>{({ name_en: t.nameEn, name_ta: t.nameTa, description_en: t.descriptionEn, description_ta: t.descriptionTa })[key]}
        <input required={key.startsWith("name")} maxLength={key.startsWith("name") ? 160 : 2000} value={draft[key]} onChange={e => setDraft(old => ({ ...old, [key]: e.target.value }))} /></label>)}
      <label>{t.price}<input type="number" min="0" max="999999999.99" step="0.01" value={draft.price ?? ""} onChange={e => setDraft(old => ({ ...old, price: e.target.value || null }))} /></label>
      <label>{t.currency}<select value={draft.currency} onChange={e => setDraft(old => ({ ...old, currency: e.target.value as ItemFields["currency"] }))}>{["INR", "USD", "EUR", "GBP"].map(v => <option key={v}>{v}</option>)}</select></label>
      <label><input type="checkbox" checked={draft.available} onChange={e => setDraft(old => ({ ...old, available: e.target.checked }))} />{t.available}</label>
    </div><button disabled={command.blocked} type="submit">{editing ? t.save : t.add}</button></fieldset></form>
    <button type="button" disabled={command.busy || command.pending || (command.stale && !loaded)} onClick={() => { select(latest ?? editing); command.reconcile(); }}>{editing ? t.useSaved : t.discard}</button>
    <SavedReview command={command} loaded={loaded} onLoad={() => void load()} onReconcile={() => { if (latest) setEditing(latest); setLoaded(false); }} t={t}>
      {(latest ? [latest] : data.items).map(i => <p key={i.id}>{i.name_en} / {i.name_ta} · v{i.version} · {i.price} {i.currency} · {i.description_en} · {i.description_ta}</p>)}
    </SavedReview>
    <p>{data.settings?.published ? t.shared : t.private}</p><p>{t.shareNote}</p>
    <button type="button" disabled={command.blocked || dirty} onClick={() => command.run<Catalogue["settings"]>(`${base}/catalogue/sharing`, { expected_version: data.settings?.version ?? 0, published: !data.settings?.published }, settings => setData(old => ({ ...old, settings })))}>{data.settings?.published ? t.revoke : t.publish}</button>
    {data.settings?.published && <p><a target="_blank" rel="noreferrer" href={`/${locale}/shared/catalogue/${data.settings.share_id}`}>{t.share}</a></p>}
  </section>;
}
