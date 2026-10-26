"use client";
import { useState } from "react";
import { toolsCopy, type ToolsLocale } from "../../../lib/business-tools-copy";
import { type Card, type CardFields, type Command, CommandState, read, useCommand, useDirtyGuard } from "./client";

const empty: CardFields = { name_en: "", name_ta: "", tagline_en: "", tagline_ta: "", description_en: "", description_ta: "", phone: "", email: "", website: "", address_en: "", address_ta: "" };
function fields(card: CardFields): CardFields { return Object.fromEntries(Object.keys(empty).map(key => [key, card[key as keyof CardFields]])) as CardFields; }

export function SavedReview({ command, loaded, onLoad, onReconcile, children, t }: { command: Command; loaded: boolean; onLoad: () => void; onReconcile: () => void; children: React.ReactNode; t: typeof toolsCopy[ToolsLocale] }) {
  return <><button type="button" disabled={command.busy} onClick={onLoad}>{t.refresh}</button>
    {loaded && <details open={command.stale}><summary>{t.compare}</summary>{children}</details>}
    {command.stale && loaded && <button type="button" onClick={() => { onReconcile(); command.reconcile(); }}>{t.reconcile}</button>}</>;
}

export default function CardEditor({ base, locale, initial }: { base: string; locale: ToolsLocale; initial: Card | null }) {
  const t = toolsCopy[locale];
  const [saved, setSaved] = useState(initial);
  const [draft, setDraft] = useState<CardFields>(() => fields(initial ?? empty));
  const [loaded, setLoaded] = useState(false);
  const [loadError, setLoadError] = useState("");
  const command = useCommand(t);
  const dirty = JSON.stringify(draft) !== JSON.stringify(fields(saved ?? empty));
  useDirtyGuard(dirty || command.pending);
  async function load() {
    try { setSaved(await read<Card | null>(`${base}/card`)); setLoaded(true); setLoadError(""); }
    catch { setLoadError(t.unavailable); }
  }
  function accept(card: Card) { setSaved(card); setDraft(fields(card)); setLoaded(false); }
  const label = (key: keyof CardFields) => ({ name_en: t.nameEn, name_ta: t.nameTa, tagline_en: t.taglineEn, tagline_ta: t.taglineTa,
    description_en: t.descriptionEn, description_ta: t.descriptionTa, phone: t.phone, email: t.email, website: t.website, address_en: t.addressEn, address_ta: t.addressTa })[key];
  return <section className="program-panel"><h2>{t.card}</h2><CommandState command={command} t={t} /><p role="status">{loadError}</p>
    <form onSubmit={event => { event.preventDefault(); command.run<Card>(`${base}/card`, { ...draft, expected_version: saved?.version ?? 0 }, accept); }}>
      <fieldset disabled={command.busy || command.pending}><div className="tools-fields">
        {(Object.keys(empty) as (keyof CardFields)[]).map(key => <label key={key}>{label(key)}
          {key.startsWith("description") || key.startsWith("address") ? <textarea maxLength={key.startsWith("description") ? 2000 : 500} value={draft[key]} onChange={e => setDraft(old => ({ ...old, [key]: e.target.value }))} />
            : <input type={key === "email" ? "email" : key === "website" ? "url" : "text"} required={key.startsWith("name_")} maxLength={key.startsWith("name") ? 160 : key.startsWith("tagline") ? 240 : key === "phone" ? 40 : key === "website" ? 500 : 254} value={draft[key]} onChange={e => setDraft(old => ({ ...old, [key]: e.target.value }))} />}
        </label>)}
      </div><button disabled={command.blocked} type="submit">{t.save}</button></fieldset>
    </form>
    <button type="button" disabled={command.busy || command.pending || (command.stale && !loaded)} onClick={() => { setDraft(fields(saved ?? empty)); command.reconcile(); }}>{saved ? t.useSaved : t.discard}</button>
    <SavedReview command={command} loaded={loaded} onLoad={() => void load()} onReconcile={() => setLoaded(false)} t={t}>
      {saved ? <><p>{saved.name_en} / {saved.name_ta} · v{saved.version}</p><p>{saved.description_en}</p><p>{saved.description_ta}</p><p>{saved.email} {saved.phone}</p>
        </> : <p>{t.noItems}</p>}
    </SavedReview>
    <h3>{t.preview}</h3><article className="tools-card" lang={locale}><h4>{locale === "ta" ? draft.name_ta : draft.name_en}</h4>
      <p>{locale === "ta" ? draft.tagline_ta : draft.tagline_en}</p><p>{locale === "ta" ? draft.description_ta : draft.description_en}</p>
      <p>{draft.phone} {draft.email}</p><p>{locale === "ta" ? draft.address_ta : draft.address_en}</p><p>{draft.website}</p></article>
    {saved && <><p>{saved.published ? t.shared : t.private}</p><p>{t.shareNote}</p>{dirty && <p>{t.saveFirst}</p>}
      <button type="button" disabled={command.blocked || (dirty && !saved.published)} onClick={() => command.run<Card>(`${base}/card/sharing`, { expected_version: saved.version, published: !saved.published }, card => { setSaved(card); })}>{saved.published ? t.revoke : t.publish}</button>
      {saved.published && <a target="_blank" rel="noreferrer" href={`/${locale}/shared/card/${saved.share_id}`}>{t.share}</a>}
      <p><a download href={`${base}/card/artifact`}>{t.download}</a></p></>}
  </section>;
}
