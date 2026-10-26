"use client";
import { useState } from "react";
import { toolsCopy, type ToolsLocale } from "../../../lib/business-tools-copy";
import { CommandState, type Item, type Line, localInput, type Page, Pager, type Quote, type QuoteFields, read, useCommand, useDirtyGuard } from "./client";
import { SavedReview } from "./card";
const line = (): Line => ({ description: "", quantity: "1.000", unit_price: "0.00", catalogue_item_id: null, catalogue_version: null });
const empty = (): QuoteFields => ({ customer_name: "", customer_address: "", issued_on: localInput(new Date().toISOString()).slice(0, 10), valid_until: null, currency: "INR", notes: "", discount: "0.00", lines: [line()] });
function fields(q: QuoteFields): QuoteFields { return { customer_name: q.customer_name, customer_address: q.customer_address, issued_on: q.issued_on, valid_until: q.valid_until, currency: q.currency, notes: q.notes, discount: q.discount, lines: q.lines.map(i => ({ description: i.description, quantity: i.quantity, unit_price: i.unit_price, catalogue_item_id: i.catalogue_item_id, catalogue_version: i.catalogue_version })) }; }

export default function QuotesEditor({ base, locale, initial, items }: { base: string; locale: ToolsLocale; initial: Page<Quote>; items: Item[] }) {
  const t = toolsCopy[locale]; const command = useCommand(t);
  const [data, setData] = useState(initial); const [editing, setEditing] = useState<Quote | null>(null);
  const [baseline, setBaseline] = useState(empty); const [draft, setDraft] = useState<QuoteFields>(baseline);
  const [loaded, setLoaded] = useState(false); const [reviewed, setReviewed] = useState(false); const [error, setError] = useState("");
  const dirty = JSON.stringify(draft) !== JSON.stringify(baseline);
  useDirtyGuard(dirty || command.pending);
  function select(q: Quote | null) { const value = fields(q ?? empty()); setEditing(q); setDraft(value); setBaseline(value); setReviewed(false); setLoaded(false); }
  function accept(q: Quote) { select(q); setData(old => ({ ...old, items: old.items.some(i => i.id === q.id) ? old.items.map(i => i.id === q.id ? q : i) : [q, ...old.items].slice(0, 25) })); }
  async function load(offset = data.offset) {
    try { setData(await read<Page<Quote>>(`${base}/quotes?limit=25&offset=${offset}`));
      if (editing) setEditing(await read<Quote>(`${base}/quotes/${editing.id}`)); setLoaded(true); setReviewed(false); setError(""); }
    catch { setError(t.unavailable); }
  }
  const patchLine = (index: number, patch: Partial<Line>) => setDraft(old => ({ ...old, lines: old.lines.map((i, n) => n === index ? { ...i, ...patch } : i) }));
  const locked = command.busy || command.pending || editing?.status === "issued";
  return <section className="program-panel"><h2>{t.quotes}</h2><p>{t.quoteNote}</p><CommandState command={command} t={t} /><p role="status">{error}</p>
    <ul className="program-list">{data.items.map(q => <li key={q.id}><strong>{q.customer_name}</strong> {q.status === "issued" ? t.issued : t.draft} · {q.total} {q.currency}
      <button type="button" disabled={command.blocked || dirty} onClick={() => select(q)}>{t.edit}</button></li>)}</ul>
    {!data.items.length && <p>{t.noItems}</p>}<Pager offset={data.offset} count={data.items.length} busy={command.blocked || dirty} onChange={offset => void load(offset)} t={t} />
    <button type="button" disabled={command.blocked || dirty} onClick={() => select(null)}>{t.newQuote}</button>
    <form onSubmit={event => { event.preventDefault(); command.run<Quote>(editing ? `${base}/quotes/${editing.id}/update` : `${base}/quotes`, { ...draft, ...(editing ? { expected_version: editing.version } : {}) }, accept); }}>
      <fieldset disabled={locked}><div className="tools-fields">
        <label>{t.customer}<input required minLength={1} maxLength={160} value={draft.customer_name} onChange={e => setDraft(old => ({ ...old, customer_name: e.target.value }))} /></label>
        <label>{t.customerAddress}<textarea maxLength={1000} value={draft.customer_address} onChange={e => setDraft(old => ({ ...old, customer_address: e.target.value }))} /></label>
        <label>{t.issuedOn}<input type="date" required value={draft.issued_on} onChange={e => setDraft(old => ({ ...old, issued_on: e.target.value }))} /></label>
        <label>{t.validUntil}<input type="date" min={draft.issued_on} value={draft.valid_until ?? ""} onChange={e => setDraft(old => ({ ...old, valid_until: e.target.value || null }))} /></label>
        <label>{t.currency}<select value={draft.currency} onChange={e => setDraft(old => ({ ...old, currency: e.target.value as QuoteFields["currency"], lines: old.lines.map(item => item.catalogue_item_id ? { ...item, catalogue_item_id: null, catalogue_version: null, unit_price: "0.00" } : item) }))}>{["INR", "USD", "EUR", "GBP"].map(v => <option key={v}>{v}</option>)}</select></label>
        <label>{t.discount}<input type="number" required min="0" max="999999999.99" step="0.01" value={draft.discount} onChange={e => setDraft(old => ({ ...old, discount: e.target.value }))} /></label>
        <label>{t.notes}<textarea maxLength={2000} value={draft.notes} onChange={e => setDraft(old => ({ ...old, notes: e.target.value }))} /></label>
      </div><h3>{t.lines}</h3><ol className="tools-lines">{draft.lines.map((item, index) => <li key={index}>
        <label>{t.fromCatalogue}<select value={item.catalogue_item_id ?? ""} onChange={e => { const product = items.find(i => i.id === e.target.value); patchLine(index, product ? { catalogue_item_id: product.id, catalogue_version: product.version, description: locale === "ta" ? product.name_ta : product.name_en, unit_price: product.price ?? "0.00" } : { catalogue_item_id: null, catalogue_version: null }); }}>
          <option value="">{t.manual}</option>{items.filter(i => i.available && i.price !== null && i.currency === draft.currency).map(i => <option key={i.id} value={i.id}>{locale === "ta" ? i.name_ta : i.name_en}</option>)}
          {item.catalogue_item_id && !items.some(i => i.id === item.catalogue_item_id && i.available && i.price !== null && i.currency === draft.currency) && <option value={item.catalogue_item_id}>{item.description}</option>}</select></label>
        {item.catalogue_item_id && <button type="button" disabled={!items.some(i => i.id === item.catalogue_item_id && i.available && i.price !== null && i.currency === draft.currency)} onClick={() => {
          const current = items.find(i => i.id === item.catalogue_item_id);
          if (current?.available && current.price !== null && current.currency === draft.currency) patchLine(index, { description: locale === "ta" ? current.name_ta : current.name_en, unit_price: current.price, catalogue_version: current.version });
        }}>{t.refreshLine}</button>}
        <div className="tools-fields"><label>{t.description}<input required maxLength={500} value={item.description} onChange={e => patchLine(index, { description: e.target.value })} /></label>
          <label>{t.quantity}<input required type="number" min="0.001" max="999999.999" step="0.001" value={item.quantity} onChange={e => patchLine(index, { quantity: e.target.value })} /></label>
          <label>{t.unitPrice}<input required type="number" min="0" max="999999999.99" step="0.01" readOnly={!!item.catalogue_item_id} value={item.unit_price} onChange={e => patchLine(index, { unit_price: e.target.value })} /></label></div>
        <button type="button" disabled={draft.lines.length <= 1} onClick={() => setDraft(old => ({ ...old, lines: old.lines.filter((_, i) => i !== index) }))}>{t.remove}</button>
      </li>)}</ol><button type="button" disabled={draft.lines.length >= 30} onClick={() => setDraft(old => ({ ...old, lines: [...old.lines, line()] }))}>{t.addLine}</button>
      <button type="submit" disabled={command.blocked}>{t.save}</button></fieldset>
    </form>
    <button type="button" disabled={command.busy || command.pending || (command.stale && !loaded)} onClick={() => { select(editing); command.reconcile(); }}>{editing ? t.useSaved : t.discard}</button>
    <SavedReview command={command} loaded={loaded} onLoad={() => void load()} onReconcile={() => { if (editing) setBaseline(fields(editing)); setLoaded(false); }} t={t}>
      {editing && <><p>{editing.customer_name} · v{editing.version} · {editing.status === "issued" ? t.issued : t.draft}</p>
        <p>{editing.lines.map(i => `${i.description}: ${i.quantity} × ${i.unit_price}`).join("; ")}</p><p>{editing.notes}</p><p>{editing.total} {editing.currency}</p>
        </>}
    </SavedReview>
    {editing && <><dl><dt>{t.subtotal}</dt><dd>{editing.subtotal} {editing.currency}</dd><dt>{t.discount}</dt><dd>{editing.discount}</dd><dt>{t.total}</dt><dd>{editing.total} {editing.currency}</dd></dl>
      {editing.status === "draft" && <><label><input type="checkbox" checked={reviewed} disabled={dirty || command.blocked} onChange={e => setReviewed(e.target.checked)} />{t.issueConfirm}</label>
        {dirty && <p>{t.saveFirst}</p>}<button type="button" disabled={!reviewed || dirty || command.blocked} onClick={() => command.run<Quote>(`${base}/quotes/${editing.id}/issue`, { expected_version: editing.version }, accept)}>{t.issue}</button></>}
      {editing.status === "issued" && <a download href={`${base}/quotes/${editing.id}/artifact`}>{t.download}</a>}</>}
  </section>;
}
