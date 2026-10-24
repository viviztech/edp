"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { components } from "../lib/api-contracts";
import { documentRequest } from "../lib/application-document-client";
import { learningFileWords } from "../lib/learning-file-messages";
import { LearningFileSummary, LearningFileUpload, type LearningLocale } from "./learning-file-upload";

type Policy = components["schemas"]["FilePolicyView"];
type Policies = components["schemas"]["FilePolicyList"];
type Rule = components["schemas"]["AssignmentFileRuleView"];
type Course = components["schemas"]["AdminCourseView"];
type Material = components["schemas"]["MaterialFileView"];
type Materials = components["schemas"]["MaterialFileList"];

function usePublishedPolicies(org: string, purpose: "assignment_submission" | "lms_material", enabled: boolean) {
  const [items, setItems] = useState<Policy[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const lock = useRef(false);
  const path = `/api/file-policies/organizations/${org}/policies?purpose=${purpose}&limit=25`;
  const load = useCallback(async (after?: string) => {
    if (!enabled || lock.current) return;
    lock.current = true; setBusy(true);
    try {
      const result = await documentRequest<Policies>(path + (after ? `&cursor=${after}` : ""));
      setItems(current => [...(after ? current : []), ...result.items.filter(item => item.state === "published")]
        .filter((item, index, all) => all.findIndex(other => other.id === item.id) === index));
      setCursor(result.next_cursor ?? null); setFailed(false);
    } catch { setFailed(true); }
    finally { lock.current = false; setBusy(false); }
  }, [enabled, path]);
  useEffect(() => { let active = true; void Promise.resolve().then(() => { if (active) return load(); }); return () => { active = false; }; }, [load]);
  return { items, cursor, busy, failed, load };
}

export function AssignmentRuleEditor({ org, courseId, assignmentId, locale, editable, canViewPolicies, disabled = false, onDirty, onSaved }: {
  org: string; courseId: string; assignmentId: string; locale: LearningLocale;
  editable: boolean; canViewPolicies: boolean; disabled?: boolean; onDirty: (dirty: boolean) => void; onSaved: () => Promise<void>;
}) {
  const text = learningFileWords[locale];
  const path = `/api/courses/organizations/${org}/courses/${courseId}/assignments/${assignmentId}/file-rule`;
  const [saved, setSaved] = useState<Rule | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [policy, setPolicy] = useState("");
  const [minimum, setMinimum] = useState("");
  const [maximum, setMaximum] = useState("");
  const [version, setVersion] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [reviewNeeded, setReviewNeeded] = useState(false);
  const [latest, setLatest] = useState<{ rule: Rule | null } | null>(null);
  const [message, setMessage] = useState("");
  const lock = useRef(false);
  const callbacks = useRef({ onDirty, onSaved });
  useEffect(() => { callbacks.current = { onDirty, onSaved }; }, [onDirty, onSaved]);
  const policies = usePublishedPolicies(org, "assignment_submission", editable && canViewPolicies);
  const dirty = loaded && (policy !== (saved?.policy_id ?? "") || minimum !== (saved ? String(saved.minimum_files) : "")
    || maximum !== (saved ? String(saved.maximum_files) : ""));
  useEffect(() => { callbacks.current.onDirty(editable && canViewPolicies && (!loaded || dirty || busy || reviewNeeded)); }, [editable, canViewPolicies, loaded, dirty, busy, reviewNeeded]);
  useEffect(() => () => callbacks.current.onDirty(false), []);

  useEffect(() => {
    let active = true;
    documentRequest<Rule | null>(path).then(rule => {
      if (!active) return;
      setSaved(rule); setVersion(rule?.version ?? null); setPolicy(rule?.policy_id ?? "");
      setMinimum(rule ? String(rule.minimum_files) : ""); setMaximum(rule ? String(rule.maximum_files) : "");
      setLoaded(true);
    }).catch(() => { if (active) setMessage(text.error); });
    return () => { active = false; };
  }, [path, text.error]);

  async function save() {
    if (lock.current || disabled || !editable || !canViewPolicies || !loaded || reviewNeeded) return;
    const min = Number(minimum), max = Number(maximum);
    if (!policy || minimum === "" || maximum === "" || !Number.isInteger(min) || !Number.isInteger(max)
      || min < 0 || max < 1 || min > max || max > 100) { setMessage(text.noDefaults); return; }
    if (!window.confirm(text.confirmRule)) return;
    lock.current = true; setBusy(true);
    try {
      const result = await documentRequest<Rule>(path, "PUT", {
        policy_id: policy, minimum_files: min, maximum_files: max, expected_version: version,
      });
      setSaved(result); setVersion(result.version); setPolicy(result.policy_id);
      setMinimum(String(result.minimum_files)); setMaximum(String(result.maximum_files)); setMessage(text.saved);
      await callbacks.current.onSaved();
    } catch { setReviewNeeded(true); setLatest(null); setMessage(text.conflict); }
    finally { lock.current = false; setBusy(false); }
  }

  async function review() {
    if (lock.current) return;
    lock.current = true; setBusy(true);
    try { setLatest({ rule: await documentRequest<Rule | null>(path) }); setMessage(""); }
    catch { setMessage(text.error); }
    finally { lock.current = false; setBusy(false); }
  }

  const policyInList = policies.items.some(item => item.id === policy);
  return <section className="learning-files" aria-label={text.ruleTitle}>
    <h4>{text.ruleTitle}</h4>
    {!editable && <p>{text.readOnly}</p>}
    {!saved && loaded && <p>{text.noRule}</p>}
    {saved && <p>{text.minimum}: {saved.minimum_files} · {text.maximum}: {saved.maximum_files} · {text.version}: {saved.version}<br />
      {text.formats}: {saved.allowed_mime_types.join(", ")} · {text.limit}: {saved.max_file_bytes}<br />
      {locale === "ta" ? saved.notice_ta : saved.notice_en}</p>}
    {editable && canViewPolicies && <>
      <p>{text.noDefaults}</p>
      <fieldset disabled={!loaded || busy || disabled}>
        <label>{text.policy}<select value={policy} onChange={event => setPolicy(event.target.value)}>
          <option value="">{text.choose}</option>
          {policy && !policyInList && <option value={policy}>{policy}</option>}
          {policies.items.map(item => <option key={item.id} value={item.id}>{item.name} · {item.edition}</option>)}
        </select></label>
        <div className="learning-file-grid">
          <label>{text.minimum}<input type="number" min="0" max="100" value={minimum} onChange={event => setMinimum(event.target.value)} /></label>
          <label>{text.maximum}<input type="number" min="1" max="100" value={maximum} onChange={event => setMaximum(event.target.value)} /></label>
        </div>
      </fieldset>
      {policies.cursor && <button type="button" disabled={policies.busy || busy} onClick={() => void policies.load(policies.cursor!)}>{text.morePolicies}</button>}
      {policies.failed && <><p>{text.error}</p><button type="button" disabled={busy || policies.busy} onClick={() => void policies.load()}>{text.refresh}</button></>}
      <div className="learning-file-actions">
        <button type="button" disabled={busy || disabled || !loaded || !dirty || reviewNeeded} onClick={() => void save()}>{text.configure}</button>
        {dirty && <button type="button" disabled={busy} onClick={() => {
          if (!window.confirm(text.discard)) return;
          setPolicy(saved?.policy_id ?? ""); setMinimum(saved ? String(saved.minimum_files) : "");
          setMaximum(saved ? String(saved.maximum_files) : "");
          // An unknown write still requires an authoritative read after discarding edits.
        }}>{text.cancel}</button>}
        {(reviewNeeded || !loaded) && <button type="button" disabled={busy} onClick={() => void review()}>{text.reviewRule}</button>}
      </div>
      {latest && <aside aria-label={text.latest}>
        <strong>{text.latest}</strong><p>{latest.rule ? `${latest.rule.policy_id} · ${text.minimum}: ${latest.rule.minimum_files} · ${text.maximum}: ${latest.rule.maximum_files} · ${text.version}: ${latest.rule.version}` : text.noRule}</p>
        <button type="button" disabled={busy} onClick={() => {
          setSaved(latest.rule); setVersion(latest.rule?.version ?? null); setLatest(null); setReviewNeeded(false);
          setLoaded(true);
        }}>{text.acceptVersion}</button>
      </aside>}
    </>}
    <p role="status">{busy ? text.working : message}</p>
  </section>;
}

export function LearningMaterialManager({ org, course, locale, canUpload, externalBusy, onDirty, onSaved }: {
  org: string; course: Course; locale: LearningLocale; canUpload: boolean; externalBusy: boolean;
  onDirty: (dirty: boolean) => void; onSaved: () => Promise<void>;
}) {
  const text = learningFileWords[locale];
  const root = `/api/courses/organizations/${org}`;
  const path = root + `/courses/${course.id}/material-files`;
  const [saved, setSaved] = useState<Materials | null>(null);
  const [lessonId, setLessonId] = useState("");
  const [policyId, setPolicyId] = useState("");
  const [position, setPosition] = useState("");
  const [labelEn, setLabelEn] = useState("");
  const [labelTa, setLabelTa] = useState("");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const [pending, setPending] = useState(false);
  const [resume, setResume] = useState<Material | null>(null);
  const [uncertainRemove, setUncertainRemove] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const callbacks = useRef({ onDirty, onSaved });
  useEffect(() => { callbacks.current = { onDirty, onSaved }; }, [onDirty, onSaved]);
  const lock = useRef(false);
  const sequence = useRef(0);
  const editable = course.state === "draft" && canUpload;
  const policies = usePublishedPolicies(org, "lms_material", editable);
  const policy = policies.items.find(item => item.id === policyId);
  const lessons = course.modules.flatMap(module => module.lessons);
  const lesson = lessons.find(item => item.id === lessonId);
  const dirty = Boolean(lessonId || policyId || position || labelEn || labelTa || pending || resume || uncertainRemove);
  useEffect(() => { callbacks.current.onDirty(dirty || busy); }, [dirty, busy]);
  useEffect(() => () => callbacks.current.onDirty(false), []);

  const load = useCallback(async (after?: string) => {
    const serial = ++sequence.current;
    setBusy(true);
    try {
      const result = await documentRequest<Materials>(path + "?limit=25" + (after ? `&cursor=${after}` : ""));
      if (serial !== sequence.current) return;
      setSaved(current => ({ ...result, items: [...(after ? current?.items ?? [] : []), ...result.items]
        .filter((item, index, all) => all.findIndex(other => other.material_id === item.material_id) === index) }));
      setFailed(false); setMessage("");
    } catch { if (serial === sequence.current) { setFailed(true); setMessage(text.error); } }
    finally { if (serial === sequence.current) setBusy(false); }
  }, [path, text.error]);
  useEffect(() => {
    let active = true;
    const generation = sequence;
    void Promise.resolve().then(() => { if (active) return load(); });
    return () => { active = false; generation.current++; };
  }, [load]);
  const scanning = saved?.items.some(item => ["quarantined", "scanning"].includes(item.file.state)) ?? false;
  useEffect(() => {
    if (!scanning) return;
    let stopped = false, count = 0;
    let timer: ReturnType<typeof setTimeout>;
    const check = async () => {
      if (stopped) return;
      await load(); count++;
      if (!stopped && count < 20) timer = setTimeout(() => void check(), 3000);
      else if (!stopped) setMessage(text.pollStopped);
    };
    timer = setTimeout(() => void check(), 3000);
    return () => { stopped = true; clearTimeout(timer); };
  }, [load, scanning, text.pollStopped]);

  async function remove(item: Material) {
    if (lock.current || pending || !editable || !window.confirm(text.removeConfirm)) return;
    lock.current = true; setBusy(true);
    try {
      if (uncertainRemove === item.material_id) {
        const current = await documentRequest<Material>(path + `/${item.material_id}`);
        setUncertainRemove(null); await load(); await callbacks.current.onSaved();
        setMessage(current.state === "removed" ? text.saved : text.uncertain); return;
      }
      await documentRequest(path + `/${item.material_id}`, "DELETE", { expected_version: item.version });
      await load(); await callbacks.current.onSaved(); setMessage(text.saved);
    } catch { setUncertainRemove(item.material_id); setMessage(text.uncertain); }
    finally { lock.current = false; setBusy(false); }
  }

  function clearFields() { setLessonId(""); setPolicyId(""); setPosition(""); setLabelEn(""); setLabelTa(""); setResume(null); }
  const valid = Boolean(lesson && policy && position !== "" && Number.isInteger(Number(position)) && Number(position) > 0
    && labelEn.trim() && labelTa.trim());
  const enabled = editable && Boolean(saved?.collection_enabled) && !failed && !busy && !externalBusy && !uncertainRemove && (valid || Boolean(resume));
  const label = (item: { label_en: string; label_ta: string }) => locale === "ta" ? item.label_ta : item.label_en;
  return <section className="learning-files" aria-label={text.materialTitle}>
    <h3>{text.materialTitle}</h3><p>{text.materialHint}</p>
    <p role="status">{busy ? text.loading : message}</p>
    <button type="button" disabled={busy || pending} onClick={() => void load()}>{text.refresh}</button>
    {saved && !saved.collection_enabled && <p>{text.disabled}</p>}
    {!editable && <p>{text.readOnly}</p>}
    {editable && <>
      <fieldset disabled={pending || busy || externalBusy || Boolean(resume)}>
        <label>{text.lesson}<select value={lessonId} onChange={event => setLessonId(event.target.value)}>
          <option value="">{text.materialSelect}</option>
          {lessons.map(item => <option key={item.id} value={item.id}>{locale === "ta" ? item.title_ta : item.title_en}</option>)}
        </select></label>
        <label>{text.policy}<select value={policyId} onChange={event => setPolicyId(event.target.value)}>
          <option value="">{text.choose}</option>
          {policies.items.map(item => <option key={item.id} value={item.id}>{item.name} · {item.edition}</option>)}
        </select></label>
        <label>{text.position}<input type="number" min="1" value={position} onChange={event => setPosition(event.target.value)} /></label>
        <label>{text.labelEn}<input maxLength={200} value={labelEn} onChange={event => setLabelEn(event.target.value)} /></label>
        <label>{text.labelTa}<input maxLength={200} value={labelTa} onChange={event => setLabelTa(event.target.value)} /></label>
      </fieldset>
      {policies.cursor && <button type="button" disabled={policies.busy || pending} onClick={() => void policies.load(policies.cursor!)}>{text.morePolicies}</button>}
      {policies.failed && <><p>{text.error}</p><button type="button" disabled={policies.busy || busy} onClick={() => void policies.load()}>{text.refresh}</button></>}
      {!policy && policies.items.length === 0 && !policies.busy && <p>{text.noPolicies}</p>}
      {policy && <p>{text.formats}: {policy.allowed_mime_types.join(", ")} · {text.limit}: {Math.min(saved?.max_upload_bytes ?? 0, policy.max_file_bytes)}<br />{locale === "ta" ? policy.notice_ta : policy.notice_en}</p>}
      {dirty && !pending && <button type="button" disabled={busy || externalBusy} onClick={() => { if (window.confirm(text.confirmContext)) clearFields(); }}>{text.cancel}</button>}
    </>}
    {(editable || pending) && <LearningFileUpload<Material> locale={locale} enabled={enabled}
      allowed={resume ? [resume.file.media_type] : policy?.allowed_mime_types ?? []}
      maxBytes={Math.min(saved?.max_upload_bytes ?? 0, resume?.file.byte_size ?? policy?.max_file_bytes ?? 0)}
      createPath={root + "/material-files"}
      intent={(metadata, id) => ({ ...metadata, client_request_id: id, policy_id: policyId,
        course_id: course.id, lesson_id: lessonId, position: Number(position), label_en: labelEn.trim(), label_ta: labelTa.trim() })}
      detailPath={item => path + `/${item.material_id}`} onPending={setPending} resume={resume}
      onDiscard={() => setResume(null)} onSaved={async () => { clearFields(); await load(); await callbacks.current.onSaved(); }} />}
    <ul className="learning-file-list">{saved?.items.map(item => {
      const material = lessons.flatMap(item => item.materials).find(row => row.id === item.material_id);
      return <li key={item.material_id}>
        <strong>{material ? `${material.position}. ${label(material)}` : item.material_id}</strong>
        <LearningFileSummary file={item.file} locale={locale} />
        {item.evidence && <p>{text.frozen} · {text.version} {item.evidence.file_version}</p>}
        {item.state === "removed" ? <p>{text.removed}</p> : item.usable && saved.collection_enabled && !failed
          ? <a href={path + `/${item.material_id}/content`}>{text.download}</a> : <p>{text.unavailable}</p>}
        {editable && item.state === "active" && <div className="learning-file-actions">
          {["pending", "uploading"].includes(item.file.state) && <button type="button" disabled={busy || pending || !saved.collection_enabled || failed}
            onClick={() => { if (!dirty || window.confirm(text.confirmContext)) { clearFields(); setResume(item); } }}>{text.resume}</button>}
          <button type="button" disabled={busy || pending || externalBusy || failed} onClick={() => void remove(item)}>{uncertainRemove === item.material_id ? text.review : text.remove}</button>
        </div>}
      </li>;
    })}</ul>
    {saved?.next_cursor && <button type="button" disabled={busy || pending} onClick={() => void load(saved.next_cursor!)}>{text.more}</button>}
  </section>;
}
