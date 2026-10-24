"use client";

import { useEffect, useRef, useState } from "react";
import type { components } from "../lib/api-contracts";
import { documentRequest, prepareApplicationFile, uploadApplicationFile } from "../lib/application-document-client";
import { learningFileWords } from "../lib/learning-file-messages";
import "./learning-files.css";

export type LearningLocale = "en" | "ta";
export type LearningFile = components["schemas"]["FileView"];
export type UploadView = { file: LearningFile; usable: boolean };
type Metadata = { media_type: string; byte_size: number; sha256: string };
type Recovery<T> = { source: File; payload: object; binding?: T; reviewed: boolean };

/** A metadata retry always reuses its UUID and payload. An uncertain byte write
 * must be read and explicitly resent; polling never retries writes. */
export function LearningFileUpload<T extends UploadView>({
  locale, enabled, allowed, maxBytes, createPath, intent, detailPath, onSaved,
  onPending, resume, onDiscard,
}: {
  locale: LearningLocale; enabled: boolean; allowed: readonly string[]; maxBytes: number;
  createPath: string; intent: (metadata: Metadata, requestId: string) => object;
  detailPath: (item: T) => string; onSaved: (item: T) => Promise<void> | void;
  onPending?: (pending: boolean) => void; resume?: T | null; onDiscard?: () => void;
}) {
  const text = learningFileWords[locale];
  const [source, setSource] = useState<File | null>(null);
  const [recovery, setRecovery] = useState<Recovery<T> | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [inputKey, setInputKey] = useState(0);
  const lock = useRef(false);
  const callbacks = useRef({ onPending, onSaved, onDiscard });
  useEffect(() => { callbacks.current = { onPending, onSaved, onDiscard }; }, [onPending, onSaved, onDiscard]);
  const pending = Boolean(source || recovery || busy || resume);
  useEffect(() => { callbacks.current.onPending?.(pending); }, [pending]);
  useEffect(() => () => callbacks.current.onPending?.(false), []);

  function finished(item: T) {
    setSource(null); setRecovery(null); setInputKey(value => value + 1);
    callbacks.current.onDiscard?.();
    setMessage(item.usable ? text.saved
      : ["quarantined", "scanning"].includes(item.file.state) ? text.scanning : text.unavailable);
  }

  async function sendBytes(value: Recovery<T>, binding: T) {
    const next = { ...value, binding, reviewed: false };
    setRecovery(next);
    const result = await uploadApplicationFile<T>(detailPath(binding) + "/content", value.source, binding.file.version);
    finished(result);
    await callbacks.current.onSaved(result);
  }

  async function upload() {
    if (lock.current || !enabled) return;
    lock.current = true; setBusy(true); setMessage("");
    let next = recovery;
    try {
      if (!next) {
        if (!source) throw new Error("missing_file");
        const metadata = await prepareApplicationFile(source, allowed, maxBytes);
        if (resume && (metadata.media_type !== resume.file.media_type
          || metadata.byte_size !== resume.file.byte_size || metadata.sha256 !== resume.file.sha256)) {
          setMessage(text.sourceMismatch); return;
        }
        next = { source, payload: intent(metadata, crypto.randomUUID()), binding: resume ?? undefined, reviewed: false };
        setRecovery(next);
      }
      if (next.binding) {
        // A saved intent must always be read immediately before a resumed write.
        const current = await documentRequest<T>(detailPath(next.binding));
        if (!["pending", "uploading"].includes(current.file.state)) {
          finished(current); await callbacks.current.onSaved(current); return;
        }
        if (!next.reviewed) {
          setRecovery({ ...next, binding: current, reviewed: true });
          setMessage(text.uncertain); return;
        }
        await sendBytes(next, current);
      } else {
        const binding = await documentRequest<T>(createPath, "POST", next.payload);
        await sendBytes(next, binding);
      }
    } catch {
      setMessage(next ? text.uncertain : text.invalid);
      // Never silently resend bytes after any failure, including a response lost
      // after the server committed. A fresh metadata GET must precede resend.
      setRecovery(current => current ? { ...current, reviewed: false } : current);
    } finally { lock.current = false; setBusy(false); }
  }

  async function review() {
    if (lock.current || !recovery?.binding) return;
    lock.current = true; setBusy(true);
    try {
      const current = await documentRequest<T>(detailPath(recovery.binding));
      if (!["pending", "uploading"].includes(current.file.state)) {
        finished(current); await callbacks.current.onSaved(current);
      } else {
        setRecovery({ ...recovery, binding: current, reviewed: true });
        setMessage(text.uncertain);
      }
    } catch { setMessage(text.error); }
    finally { lock.current = false; setBusy(false); }
  }

  function discard() {
    if (lock.current || !window.confirm(text.discard)) return;
    setSource(null); setRecovery(null); setInputKey(value => value + 1); setMessage("");
    callbacks.current.onDiscard?.();
  }

  return <div className="learning-file-upload" aria-busy={busy}>
    <label>{text.select}<input key={inputKey} type="file" accept={allowed.join(",")}
      disabled={!enabled || busy || Boolean(recovery)}
      onChange={event => { setSource(event.target.files?.[0] ?? null); setMessage(""); }} /></label>
    {source && <p>{source.name} · {source.size} {text.bytes}</p>}
    <div className="learning-file-actions">
      {recovery?.binding && !recovery.reviewed
        ? <button type="button" disabled={busy || !enabled} onClick={() => void review()}>{text.review}</button>
        : <button type="button" disabled={busy || !enabled || (!source && !recovery)} onClick={() => void upload()}>
          {recovery ? recovery.binding ? text.resend : text.recoverCreate : text.upload}
        </button>}
      {pending && <button type="button" disabled={busy} onClick={discard}>{text.cancel}</button>}
    </div>
    <p role="status">{busy ? text.working : message}</p>
  </div>;
}

export function LearningFileSummary({ file, locale }: { file: LearningFile; locale: LearningLocale }) {
  const text = learningFileWords[locale];
  const states = { pending: text.pending, uploading: text.uploading, quarantined: text.quarantined,
    scanning: text.scanState, clean: text.clean, infected: text.infected, rejected: text.rejected, deleted: text.deleted };
  return <>
    <p>{file.media_type} · {file.byte_size} {text.bytes} · {states[file.state]}</p>
    <small className="learning-file-digest">{text.digest}: {file.sha256}</small>
  </>;
}
