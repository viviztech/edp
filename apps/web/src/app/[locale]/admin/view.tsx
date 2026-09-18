"use client";
import { useEffect, useState } from "react";
import type { components } from "../../../lib/api-contracts";
import type { AuthMessages } from "../../../lib/auth-messages";

export default function Audit({ organization, text }: { organization: string; text: AuthMessages }) {
  const [rows, setRows] = useState<components["schemas"]["AuditView"][]>([]);
  const [offset, setOffset] = useState(0);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    fetch("/api/session/audit/" + organization + "?offset=" + offset, { cache: "no-store" })
      .then(response => { if (!response.ok) throw new Error("load"); return response.json(); })
      .then(data => { if (active) setRows(data); })
      .catch(() => { if (active) setFailed(true); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [organization, offset, revision]);
  return <section aria-busy={loading}><h2>{text.audit}</h2>
    {loading ? <p role="status">{text.loading}</p> : failed ? <p role="alert">{text.error}</p> : rows.length === 0 ? <p>{text.noAudit}</p> :
      <ul>{rows.map(row => <li key={row.id}><time dateTime={row.created_at}>{new Date(row.created_at).toLocaleString()}</time> — {row.action}</li>)}</ul>}
    <button disabled={loading} onClick={() => { setLoading(true); setFailed(false); setOffset(0); setRevision(revision + 1); }}>{text.refresh}</button>
    <button disabled={loading || rows.length < 25 || offset >= 9975} onClick={() => { setLoading(true); setFailed(false); setOffset(offset + 25); }}>{text.next}</button>
  </section>;
}
