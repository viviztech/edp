"use client";
import { useRef, useState } from "react";
import type { components } from "../../../../lib/api-contracts";
import { applicationDocumentWords } from "../../../../lib/application-document-content";
import { documentRequest } from "../../../../lib/application-document-client";
import "../../../../components/application-documents.css";
type List = components["schemas"]["ApplicationDocumentList"];

export default function ReviewerDocuments({ org, assignment, locale }: { org: string; assignment: string; locale: "en" | "ta" }) {
  const t = applicationDocumentWords[locale], root = `/api/selection/organizations/${org}/assignments/${assignment}/documents`;
  const [data, setData] = useState<List | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState(false);
  const lock = useRef(false);
  async function load(more = false) {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError(false);
    try {
      const value = await documentRequest<List>(root + `?limit=25${more && data?.next_cursor ? `&cursor=${data.next_cursor}` : ""}`);
      setData(previous => more && previous ? { ...value, items: [...previous.items, ...value.items.filter(item => !previous.items.some(row => row.id === item.id))] } : value);
    } catch { setData(null); setError(true); }
    finally { lock.current = false; setBusy(false); }
  }
  return <section className="application-documents reviewer-documents" aria-label={t.title} aria-busy={busy}>
    <h3>{t.title}</h3><button type="button" disabled={busy} onClick={() => void load()}>{data ? t.refresh : t.assignedDocuments}</button>
    {error && <p role="status">{t.failed}</p>}
    {data && <>{!data.collection_enabled && <p>{t.disabled}</p>}<p>{t.frozen}</p>
      {!data.items.length && <p>{t.noDocuments}</p>}
      <ul>{data.items.map(value => {
        const requirement = data.document_requirements.find(item => item.id === value.requirement_id), evidence = value.submitted_evidence;
        return <li key={value.id}><h4>{requirement ? locale === "ta" ? requirement.label_ta : requirement.label_en : t.title}</h4>
          {requirement && <p>{locale === "ta" ? requirement.instructions_ta : requirement.instructions_en}</p>}
          <strong>{t.states[value.file.state]}</strong><p>{value.file.media_type} · {t.bytes}: {evidence?.byte_size ?? value.file.byte_size} · {t.version}: {evidence?.file_version ?? value.file.version}</p>
          {value.file.state === "clean" && !value.usable && <p>{t.unavailable}</p>}
          <p className="application-file-digest">{t.digest}: {evidence?.sha256 ?? value.file.sha256}</p>
          {evidence && <time dateTime={evidence.frozen_at}>{new Date(evidence.frozen_at).toLocaleString(locale)}</time>}
          {data.collection_enabled && value.usable && evidence && <a download href={`${root}/${value.id}/content`}>{t.downloading}</a>}
        </li>;
      })}</ul>
      {data.next_cursor && <button type="button" disabled={busy} onClick={() => void load(true)}>{t.more}</button>}
    </>}
  </section>;
}
