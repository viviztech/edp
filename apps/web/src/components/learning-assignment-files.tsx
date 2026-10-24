"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { components } from "../lib/api-contracts";
import { documentRequest } from "../lib/application-document-client";
import { learningFileWords } from "../lib/learning-file-messages";
import { LearningFileSummary, LearningFileUpload, type LearningLocale } from "./learning-file-upload";

type FileList = components["schemas"]["AssignmentFileList"];
type FileView = components["schemas"]["AssignmentFileView"];

export function AssignmentFiles({ org, courseId, assignmentId, locale, editable, refreshKey, onReady }: {
  org: string; courseId: string; assignmentId: string; locale: LearningLocale;
  editable: boolean; refreshKey: string; onReady: (ready: boolean) => void;
}) {
  const text = learningFileWords[locale];
  const path = `/api/courses/organizations/${org}/my-learning/${courseId}/assignments/${assignmentId}/files`;
  const [saved, setSaved] = useState<FileList | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const [pending, setPending] = useState(false);
  const [resume, setResume] = useState<FileView | null>(null);
  const [message, setMessage] = useState("");
  const [uncertainRemove, setUncertainRemove] = useState<string | null>(null);
  const readyCallback = useRef(onReady);
  useEffect(() => { readyCallback.current = onReady; }, [onReady]);
  const sequence = useRef(0);
  const lock = useRef(false);
  const load = useCallback(async () => {
    const serial = ++sequence.current;
    setBusy(true);
    try {
      const result = await documentRequest<FileList>(path);
      if (serial !== sequence.current) return;
      setSaved(result);
      setSelected(current => current.filter(id => result.items.some(item => item.id === id
        && item.usable && item.state === "active" && item.target_revision === result.next_revision)));
      setFailed(false); setMessage("");
    } catch { if (serial === sequence.current) { setFailed(true); setMessage(text.error); } }
    finally { if (serial === sequence.current) setBusy(false); }
  }, [path, text.error]);
  useEffect(() => {
    let active = true;
    const generation = sequence;
    void Promise.resolve().then(() => { if (active) return load(); });
    return () => { active = false; generation.current++; };
  }, [load, refreshKey]);

  const selectedUsable = selected.filter(id => saved?.items.some(item => item.id === id && item.usable
    && item.state === "active" && item.target_revision === saved.next_revision));
  const ready = Boolean(saved && !failed && !busy && !pending && !uncertainRemove && (!saved.rule
    || ((!saved.collection_enabled ? saved.rule.minimum_files === 0 && selectedUsable.length === 0 : true)
      && selectedUsable.length >= saved.rule.minimum_files && selectedUsable.length <= saved.rule.maximum_files)));
  useEffect(() => { readyCallback.current(ready); }, [ready]);
  useEffect(() => () => readyCallback.current(false), []);

  // Bounded read-only checks. An interrupted/expired upload is never retried here.
  const scanning = saved?.items.some(item => ["quarantined", "scanning"].includes(item.file.state)) ?? false;
  useEffect(() => {
    if (!scanning) return;
    let stopped = false;
    let count = 0;
    let timer: ReturnType<typeof setTimeout>;
    const check = async () => {
      if (stopped) return;
      await load();
      count++;
      if (!stopped && count < 20) timer = setTimeout(() => void check(), 3000);
      else if (!stopped) setMessage(text.pollStopped);
    };
    timer = setTimeout(() => void check(), 3000);
    return () => { stopped = true; clearTimeout(timer); };
  }, [load, scanning, text.pollStopped]);

  async function remove(item: FileView) {
    if (lock.current || pending || !window.confirm(text.removeConfirm)) return;
    lock.current = true; setBusy(true);
    try {
      if (uncertainRemove === item.id) {
        const current = await documentRequest<FileView>(path + `/${item.id}`);
        setUncertainRemove(null); await load();
        setMessage(current.state === "removed" ? text.saved : text.uncertain);
        return; // A reconciled read never automatically repeats a DELETE.
      }
      await documentRequest(path + `/${item.id}`, "DELETE", { expected_version: item.version });
      await load(); setMessage(text.saved);
    } catch { setUncertainRemove(item.id); setMessage(text.uncertain); }
    finally { lock.current = false; setBusy(false); }
  }

  const active = saved?.items.filter(item => item.state === "active" && item.target_revision === saved.next_revision) ?? [];
  const canUpload = editable && Boolean(saved?.collection_enabled && saved.rule
    && (resume || active.length < saved.rule.maximum_files)) && !failed && !busy && !uncertainRemove;
  return <section className="learning-files" aria-label={text.title}>
    <h4>{text.title}</h4>
    <p role="status">{busy ? text.loading : message}</p>
    <button type="button" disabled={busy || pending} onClick={() => void load()}>{text.refresh}</button>
    {saved && !saved.collection_enabled && <p>{text.disabled}</p>}
    {saved && !saved.rule && <p>{text.noRule}</p>}
    {saved?.rule && <>
      <p>{text.minimum}: {saved.rule.minimum_files} · {text.maximum}: {saved.rule.maximum_files}</p>
      <p>{text.formats}: {saved.rule.allowed_mime_types.join(", ")} · {text.limit}: {Math.min(saved.max_upload_bytes, saved.rule.max_file_bytes)}</p>
      <p>{locale === "ta" ? saved.rule.notice_ta : saved.rule.notice_en}</p>
      {editable && <p>{text.cleanOnly} {text.selectCount}: {selectedUsable.length}</p>}
    </>}
    <ul className="learning-file-list">{saved?.items.filter(item => item.state !== "removed").map(item => <li key={item.id}>
      <small>{text.revision} {item.target_revision}</small>
      <LearningFileSummary file={item.file} locale={locale} />
      {item.evidence && <p>{text.frozen} · {text.version} {item.evidence.file_version}<small className="learning-file-digest">{item.evidence.sha256}</small></p>}
      {editable && item.state === "active" && item.target_revision === saved.next_revision && <label className="learning-file-check">
        <input type="checkbox" name="file_ids" value={item.id} checked={selectedUsable.includes(item.id)}
          disabled={!item.usable || !saved.collection_enabled || failed || busy || pending || Boolean(uncertainRemove)
            || (!selectedUsable.includes(item.id) && selectedUsable.length >= (saved.rule?.maximum_files ?? 0))}
          onChange={event => setSelected(current => event.target.checked ? [...current, item.id] : current.filter(id => id !== item.id))} />
        {text.use} · {item.file.id}
      </label>}
      {item.usable && saved.collection_enabled && !failed && <a href={path + `/${item.id}/content`}>{text.download}</a>}
      {!item.usable && <p>{text.unavailable}</p>}
      {editable && item.state === "active" && item.target_revision === saved.next_revision && <div className="learning-file-actions">
        {["pending", "uploading"].includes(item.file.state) && <button type="button" disabled={busy || pending || !saved.collection_enabled || failed}
          onClick={() => setResume(item)}>{text.resume}</button>}
        <button type="button" disabled={busy || pending || failed} onClick={() => void remove(item)}>
          {uncertainRemove === item.id ? text.review : text.remove}
        </button>
      </div>}
    </li>)}</ul>
    {saved?.rule && (editable || pending) && <LearningFileUpload<FileView> locale={locale} enabled={canUpload}
      allowed={saved.rule.allowed_mime_types} maxBytes={Math.min(saved.max_upload_bytes, saved.rule.max_file_bytes)}
      createPath={path} intent={(metadata, id) => ({ ...metadata, client_request_id: id, expected_revision: saved.next_revision })}
      detailPath={item => path + `/${item.id}`} onSaved={load} onPending={setPending}
      resume={resume} onDiscard={() => setResume(null)} />}
    {editable && saved?.rule && !ready && <p>{text.ruleRequired}</p>}
  </section>;
}

export function TrainerSubmissionFiles({ org, courseId, submissionId, locale }: {
  org: string; courseId: string; submissionId: string; locale: LearningLocale;
}) {
  const text = learningFileWords[locale];
  const path = `/api/courses/organizations/${org}/trainer-delivery/${courseId}/assignment-submissions/${submissionId}/files`;
  const [files, setFiles] = useState<FileView[]>([]);
  const [message, setMessage] = useState(text.loading as string);
  const [busy, setBusy] = useState(false);
  const sequence = useRef(0);
  const load = useCallback(async () => {
    const serial = ++sequence.current;
    setBusy(true);
    try {
      const result = await documentRequest<FileView[]>(path);
      if (serial === sequence.current) { setFiles(result); setMessage(""); }
    }
    catch { if (serial === sequence.current) { setFiles([]); setMessage(text.error); } }
    finally { if (serial === sequence.current) setBusy(false); }
  }, [path, text.error]);
  useEffect(() => {
    let active = true;
    const generation = sequence;
    void Promise.resolve().then(() => { if (active) return load(); });
    return () => { active = false; generation.current++; };
  }, [load]);
  return <section className="learning-files" aria-label={text.frozen}>
    <h4>{text.frozen}</h4><p role="status">{message}</p>
    <button type="button" disabled={busy} onClick={() => void load()}>{text.refresh}</button>
    {!message && files.length === 0 && <p>{text.empty}</p>}
    <ul className="learning-file-list">{files.map(item => <li key={item.id}>
      <LearningFileSummary file={item.file} locale={locale} />
      {item.evidence && <p>{text.version} {item.evidence.file_version}<small className="learning-file-digest">{item.evidence.sha256}</small></p>}
      {item.usable && item.evidence
        ? <a href={path + `/${item.id}/content`}>{text.download}</a> : <p>{text.unavailable}</p>}
    </li>)}</ul>
  </section>;
}
