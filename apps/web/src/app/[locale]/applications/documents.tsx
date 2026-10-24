"use client";
import { useEffect, useRef, useState } from "react";
import type { components } from "../../../lib/api-contracts";
import { applicationDocumentWords } from "../../../lib/application-document-content";
import { DocumentRequestError, documentRequest, prepareApplicationFile, uploadApplicationFile } from "../../../lib/application-document-client";
import "../../../components/application-documents.css";

type Document = components["schemas"]["ApplicationDocumentView"];
type DocumentList = components["schemas"]["ApplicationDocumentList"];
type DocumentResult = components["schemas"]["ApplicationDocumentResult"];
type Registration = components["schemas"]["DocumentCreate"];
type Requirement = components["schemas"]["DocumentRequirementView"];

export default function ApplicationDocuments({ org, applicationId, applicationVersion, requirements, collectionEnabled, maxUploadBytes, locale, readOnly, blocked, dirty, onBusy, onVersion, onReadiness, onPendingChange }: {
  org: string; applicationId: string; applicationVersion: number; requirements: Requirement[];
  collectionEnabled: boolean; maxUploadBytes: number; locale: "en" | "ta"; readOnly: boolean;
  blocked: boolean; dirty: boolean; onBusy: (value: boolean) => void;
  onVersion: (version: number, expected?: number) => void; onReadiness: (ready: boolean) => void;
  onPendingChange: (pending: boolean) => void;
}) {
  const t = applicationDocumentWords[locale], root = `/api/applications/organizations/${org}/applications/${applicationId}/documents`;
  const [items, setItems] = useState<Document[]>([]), [cursor, setCursor] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false), [busy, setBusy] = useState(false), [message, setMessage] = useState("");
  const [enabled, setEnabled] = useState(collectionEnabled), [runtimeMaximum, setRuntimeMaximum] = useState(maxUploadBytes);
  const [selection, setSelection] = useState<{ requirement: Requirement; replaces?: string } | null>(null);
  const [file, setFile] = useState<File | null>(null), [fileKey, setFileKey] = useState(0);
  const [pending, setPending] = useState<{ body: Registration; file: File } | null>(null);
  const [uncertain, setUncertain] = useState<string | null>(null), [continuation, setContinuation] = useState<Document | null>(null);
  const lock = useRef(false), mounted = useRef(true), pollCount = useRef(0);
  const callbacks = useRef({ onBusy, onVersion, onReadiness, onPendingChange });
  useEffect(() => { callbacks.current = { onBusy, onVersion, onReadiness, onPendingChange }; }, [onBusy, onVersion, onReadiness, onPendingChange]);
  const locked = busy || blocked || !loaded || !!pending || !!uncertain;
  const modifiable = enabled && !readOnly;
  const ready = loaded && !cursor && !pending && !uncertain && !busy && items.every(item => item.usable)
    && requirements.every(value => items.filter(item => item.requirement_id === value.id && item.usable).length >= value.min_files);
  useEffect(() => { callbacks.current.onReadiness(ready); }, [ready]);
  const unsaved = !!file || !!pending || !!uncertain;
  useEffect(() => { callbacks.current.onPendingChange(unsaved); }, [unsaved]);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; callbacks.current.onBusy(false); callbacks.current.onPendingChange(false); }; }, []);
  function sync(value: Document) {
    setItems(previous => value.removed_at || value.replaced_by_id ? previous.filter(item => item.id !== value.id) : [value, ...previous.filter(item => item.id !== value.id)]);
  }
  async function load(more = false) {
    const data = await documentRequest<DocumentList>(`${root}?limit=25${more && cursor ? `&cursor=${cursor}` : ""}`);
    if (!mounted.current) return;
    setItems(previous => more ? [...previous, ...data.items.filter(item => !previous.some(value => value.id === item.id))] : data.items);
    setCursor(data.next_cursor); setEnabled(data.collection_enabled); setRuntimeMaximum(data.max_upload_bytes); setLoaded(true);
    callbacks.current.onVersion(data.application_version);
  }
  useEffect(() => {
    let active = true;
    documentRequest<DocumentList>(root + "?limit=25").then(data => {
      if (!active) return;
      setItems(data.items); setCursor(data.next_cursor); setEnabled(data.collection_enabled); setRuntimeMaximum(data.max_upload_bytes); setLoaded(true);
      callbacks.current.onVersion(data.application_version);
    }).catch(() => { if (active) setMessage(t.failed); });
    return () => { active = false; };
  }, [root, t.failed]);
  async function run(action: () => Promise<void>) {
    if (lock.current || blocked) return;
    lock.current = true; setBusy(true); callbacks.current.onBusy(true); setMessage("");
    try { await action(); } catch { if (mounted.current) setMessage(t.failed); }
    finally { lock.current = false; if (mounted.current) { setBusy(false); callbacks.current.onBusy(false); } }
  }
  async function refreshSaved() {
    if (uncertain) {
      const result = await documentRequest<DocumentResult>(`${root}/${uncertain}`);
      sync(result.document); callbacks.current.onVersion(result.application_version);
      setContinuation(result.document.file.state === "pending" && !result.document.removed_at && !result.document.replaced_by_id ? result.document : null);
      if (result.document.file.state !== "pending" || result.document.removed_at || result.document.replaced_by_id) { setFile(null); setSelection(null); setFileKey(key => key + 1); }
      setUncertain(null); setMessage(result.document.file.state === "pending" ? t.scanning : t.saved);
    } else { await load(); setMessage(t.saved); }
  }
  async function sendBytes(value: Document, source: File) {
    setUncertain(value.id); setContinuation(null);
    try {
      const result = await uploadApplicationFile<DocumentResult>(`${root}/${value.id}/content`, source, value.file.version);
      if (!mounted.current) return;
      sync(result.document); callbacks.current.onVersion(result.application_version); setUncertain(null); setFile(null); setSelection(null); setFileKey(key => key + 1); setMessage(t.scanning); pollCount.current = 0;
    } catch { if (mounted.current) setMessage(t.uncertain); }
  }
  async function recoverRegistration() {
    if (!pending) return;
    try {
      const result = await documentRequest<DocumentResult>(root, "POST", pending.body);
      if (!mounted.current) return;
      sync(result.document); callbacks.current.onVersion(result.application_version, pending.body.expected_version);
      if (pending.body.replaces_document_id) setItems(previous => previous.filter(item => item.id !== pending.body.replaces_document_id));
      setPending(null); setContinuation(result.document.file.state === "pending" ? result.document : null); setMessage(t.saved);
    } catch (error) {
      if (error instanceof DocumentRequestError && error.status < 500) { setPending(null); setMessage(error.code === "version_conflict" ? t.changed : t.failed); await load(); }
      else setMessage(t.uncertain);
    }
  }
  async function register() {
    if (!file || !selection || !modifiable || dirty) { setMessage(dirty ? t.saveFirst : t.invalidFile); return; }
    const maximum = Math.min(runtimeMaximum, selection.requirement.file_policy.max_file_bytes, selection.requirement.file_policy.max_upload_bytes);
    let prepared: Awaited<ReturnType<typeof prepareApplicationFile<Registration["media_type"]>>>;
    try { prepared = await prepareApplicationFile(file, selection.requirement.file_policy.allowed_mime_types, maximum); }
    catch { setMessage(t.invalidFile); return; }
    const body: Registration = { ...prepared, expected_version: applicationVersion, client_request_id: crypto.randomUUID(), requirement_id: selection.requirement.id, ...(selection.replaces ? { replaces_document_id: selection.replaces } : {}) };
    setPending({ body, file });
    try {
      const result = await documentRequest<DocumentResult>(root, "POST", body);
      if (!mounted.current) return;
      sync(result.document); callbacks.current.onVersion(result.application_version, body.expected_version);
      if (selection.replaces) setItems(previous => previous.filter(item => item.id !== selection.replaces));
      setPending(null); await sendBytes(result.document, file);
    } catch (error) {
      if (error instanceof DocumentRequestError && error.status < 500) { setPending(null); setMessage(error.code === "version_conflict" ? t.changed : t.failed); await load(); }
      else setMessage(t.uncertain);
    }
  }
  async function remove(value: Document) {
    if (!modifiable || dirty || !window.confirm(t.removeConfirm)) return;
    setUncertain(value.id);
    try {
      const result = await documentRequest<DocumentResult>(`${root}/${value.id}`, "DELETE", { expected_version: applicationVersion });
      if (!mounted.current) return;
      sync(result.document); callbacks.current.onVersion(result.application_version, applicationVersion); setUncertain(null); setMessage(t.saved);
    } catch { setMessage(t.uncertain); }
  }
  // Poll reads only, for a bounded minute. Pending registrations never trigger
  // automatic byte retries, and a scan failure never becomes a clean UI state.
  const scanning = items.some(item => ["quarantined", "scanning"].includes(item.file.state));
  useEffect(() => {
    if (!scanning || busy || blocked || uncertain || pending || cursor || pollCount.current >= 20) return;
    const timer = window.setTimeout(() => {
      pollCount.current++;
      documentRequest<DocumentList>(root + "?limit=25").then(data => {
        if (!mounted.current) return;
        setItems(data.items); setCursor(data.next_cursor); setEnabled(data.collection_enabled); setRuntimeMaximum(data.max_upload_bytes); callbacks.current.onVersion(data.application_version);
      }).catch(() => { if (mounted.current) setMessage(t.failed); });
    }, 3000);
    return () => window.clearTimeout(timer);
  }, [blocked, busy, cursor, items, pending, root, scanning, t.failed, uncertain]);
  return <section className="application-documents" aria-label={t.title} aria-busy={busy}>
    <h2>{t.title}</h2><p role="status">{busy ? t.working : message}</p>
    {!enabled && <p className="application-boundary">{t.disabled}</p>}
    {readOnly && <p>{t.readOnly}</p>}{dirty && modifiable && <p>{t.saveFirst}</p>}
    <div className="application-actions"><button type="button" disabled={busy || blocked || !!pending} onClick={() => void run(refreshSaved)}>{uncertain ? t.reviewSaved : t.refresh}</button>
      {pending && <button type="button" disabled={busy || blocked} onClick={() => void run(recoverRegistration)}>{t.recoverCreate}</button>}
      {continuation && file && <button type="button" disabled={locked || dirty || !modifiable} onClick={() => void run(() => sendBytes(continuation, file))}>{t.continueUpload}</button>}
      {cursor && <button type="button" disabled={locked} onClick={() => void run(() => load(true))}>{t.more}</button>}
    </div>
    {requirements.map(requirement => {
      const current = items.filter(item => item.requirement_id === requirement.id), policy = requirement.file_policy;
      const limit = Math.min(runtimeMaximum, policy.max_file_bytes, policy.max_upload_bytes);
      return <article key={requirement.id} className="application-document-requirement"><h3>{locale === "ta" ? requirement.label_ta : requirement.label_en}</h3>
        <p>{locale === "ta" ? requirement.instructions_ta : requirement.instructions_en}</p>
        <p>{t.minimumRequired}: {requirement.min_files} · {t.maximumAllowed}: {requirement.max_files} · {t.count}: {current.length}</p>
        <dl><dt>{t.formats}</dt><dd>{policy.allowed_mime_types.join(", ")}</dd><dt>{t.uploadLimit}</dt><dd>{limit}</dd><dt>{t.policyMaximum}</dt><dd>{policy.max_files}</dd><dt>{t.retention}</dt><dd>{policy.retention_days}</dd><dt>{t.rejectedRetention}</dt><dd>{policy.rejected_retention_days}</dd><dt>{t.notice}</dt><dd>{locale === "ta" ? policy.notice_ta : policy.notice_en}</dd></dl>
        <ul>{current.map(value => <li key={value.id}><strong>{t.states[value.file.state]}</strong><p>{value.file.media_type} · {t.bytes}: {value.file.byte_size} · {t.version}: {value.file.version}</p>
          {value.file.state === "clean" && !value.usable && <p>{t.unavailable}</p>}
          <p className="application-file-digest">{t.digest}: {value.file.sha256}</p>
          {value.submitted_evidence && <p>{t.frozen} · {t.version}: {value.submitted_evidence.file_version} · {value.submitted_evidence.byte_size} · <time dateTime={value.submitted_evidence.frozen_at}>{new Date(value.submitted_evidence.frozen_at).toLocaleString(locale)}</time><span className="application-file-digest">{value.submitted_evidence.sha256}</span></p>}
          {enabled && value.usable && <a download href={`${root}/${value.id}/content`}>{t.downloading}</a>}
          {modifiable && <div className="application-actions"><button type="button" disabled={locked || dirty} onClick={() => { setSelection({ requirement, replaces: value.id }); setFile(null); setContinuation(null); setFileKey(key => key + 1); setMessage(t.reselect); }}>{t.replace}</button><button type="button" disabled={locked || dirty} onClick={() => void run(() => remove(value))}>{t.removeDocument}</button></div>}
        </li>)}</ul>
        {modifiable && <button type="button" disabled={locked || dirty || !!cursor || current.length >= requirement.max_files || items.filter(item => requirements.find(row => row.id === item.requirement_id)?.file_policy_id === requirement.file_policy_id).length >= policy.max_files} onClick={() => { setSelection({ requirement }); setFile(null); setContinuation(null); setFileKey(key => key + 1); setMessage(""); }}>{t.upload}</button>}
      </article>;
    })}
    {selection && modifiable && !pending && !uncertain && !continuation && <form className="application-document-picker" onSubmit={event => { event.preventDefault(); void run(register); }}>
      <h3>{locale === "ta" ? selection.requirement.label_ta : selection.requirement.label_en}</h3>
      <label>{t.selectFile}<input key={fileKey} type="file" accept={selection.requirement.file_policy.allowed_mime_types.join(",")} disabled={locked || dirty} onChange={event => setFile(event.target.files?.[0] ?? null)} /></label>
      <button disabled={locked || dirty || !file} type="submit">{t.send}</button><button type="button" disabled={locked} onClick={() => { setSelection(null); setFile(null); setContinuation(null); }}>{t.cancel}</button>
    </form>}
    {!ready && loaded && <p>{t.cleanRequired}</p>}
  </section>;
}
