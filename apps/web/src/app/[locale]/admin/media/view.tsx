"use client";
import { useEffect, useRef, useState } from "react";
import type { components } from "../../../../lib/api-contracts";
import { mediaAdminMessages } from "../../../../lib/media-admin-messages";
import type { Locale } from "../../../../lib/messages";

type Asset = components["schemas"]["AssetView"];
type Batch = components["schemas"]["AssetList"];

export default function MediaMetadata({ org, locale }: { org: string; locale: Locale }) {
  const text = mediaAdminMessages[locale];
  const base = `/api/cms/organizations/${org}/assets`;
  const [items, setItems] = useState<Asset[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);
  const [message, setMessage] = useState("");
  const locked = useRef(false);
  useEffect(() => {
    let active = true;
    fetch(base, { cache: "no-store" }).then(async response => {
      if (!response.ok) throw new Error(); return response.json() as Promise<Batch>;
    }).then(data => { if (active) { setItems(data.items); setCursor(data.next_cursor); } })
      .catch(() => { if (active) setMessage(text.error); }).finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [base, text.error]);
  async function load(more = false) {
    if (locked.current || busy) return;
    locked.current = true; setBusy(true); setMessage("");
    try {
      const response = await fetch(base + (more && cursor ? `?${new URLSearchParams({ cursor })}` : ""), { cache: "no-store" });
      if (!response.ok) throw new Error();
      const data = await response.json() as Batch;
      setItems(previous => more ? [...previous, ...data.items.filter(item => !previous.some(old => old.id === item.id))] : data.items);
      setCursor(data.next_cursor);
    } catch { setMessage(text.error); } finally { locked.current = false; setBusy(false); }
  }
  return <section aria-busy={busy}>
    <p className="notice">{text.boundary}</p>
    <p role="status">{busy ? text.loading : message}</p>
    <button disabled={busy} onClick={() => load()}>{text.refresh}</button>
    {!busy && !message && !items.length && <p>{text.empty}</p>}
    <ul className="media-metadata-list">{items.map(item => <li key={item.id}>
      <h2>{item.title}</h2><dl>
        <dt>{text.filename}</dt><dd>{item.filename}</dd>
        <dt>{text.mediaType}</dt><dd>{item.media_type}</dd>
        <dt>{text.size}</dt><dd>{item.byte_size.toLocaleString(locale)}</dd>
        <dt>{text.scan}</dt><dd>{text[item.scan_status]}</dd>
        <dt>{text.visibility}</dt><dd>{text[item.visibility]}</dd>
      </dl>
    </li>)}</ul>
    {cursor && <button disabled={busy} onClick={() => load(true)}>{text.more}</button>}
  </section>;
}
