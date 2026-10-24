"use client";
import { useEffect, useRef, useState } from "react";
import type { FilePolicy, FilePolicyList } from "../../../../lib/file-policy-content";
import { applicationDocumentWords, newDocumentRequirement, type DraftDocumentRequirement } from "../../../../lib/application-document-content";
import "../../../../components/application-documents.css";

export default function DocumentRequirementsEditor({ org, locale, values, onChange, disabled, canViewPolicies }: {
  org: string; locale: "en" | "ta"; values: DraftDocumentRequirement[];
  onChange: (values: DraftDocumentRequirement[]) => void; disabled: boolean; canViewPolicies: boolean;
}) {
  const t = applicationDocumentWords[locale];
  const [policies, setPolicies] = useState<FilePolicy[]>([]), [cursor, setCursor] = useState<string | null>(null);
  const [busy, setBusy] = useState(false), [error, setError] = useState(false);
  const paging = useRef(false);
  const base = `/api/file-policies/organizations/${org}/policies?purpose=application_document&limit=25`;
  useEffect(() => {
    if (!canViewPolicies) return;
    let active = true;
    fetch(base, { cache: "no-store" }).then(async response => { if (!response.ok) throw new Error(); return response.json() as Promise<FilePolicyList>; })
      .then(data => { if (active) { setPolicies(data.items); setCursor(data.next_cursor); setError(false); } })
      .catch(() => { if (active) setError(true); });
    return () => { active = false; };
  }, [base, canViewPolicies]);
  async function load(more: boolean) {
    if (paging.current) return;
    paging.current = true; setBusy(true);
    try {
      const response = await fetch(base + (more && cursor ? `&cursor=${cursor}` : ""), { cache: "no-store" });
      if (!response.ok) throw new Error();
      const data = await response.json() as FilePolicyList;
      setPolicies(previous => more ? [...previous, ...data.items.filter(value => !previous.some(item => item.id === value.id))] : data.items);
      setCursor(data.next_cursor); setError(false);
    } catch { setError(true); }
    finally { paging.current = false; setBusy(false); }
  }
  const published = policies.filter(value => value.state === "published" && value.purpose === "application_document");
  function update(index: number, patch: Partial<DraftDocumentRequirement>) {
    onChange(values.map((value, position) => position === index ? { ...value, ...patch } : value));
  }
  function move(index: number, offset: number) {
    const result = [...values], target = index + offset;
    if (target < 0 || target >= result.length) return;
    [result[index], result[target]] = [result[target], result[index]]; onChange(result);
  }
  const locked = disabled || !canViewPolicies;
  function add() {
    let next = 1;
    while (values.some(value => value.key === `document_${next}`)) next++;
    onChange([...values, newDocumentRequirement(`document_${next}`)]);
  }
  return <section className="definition-documents" aria-label={t.title}>
    <div className="definition-section-head"><h3>{t.title}</h3>
      {!disabled && <button type="button" disabled={locked || values.length >= 20} onClick={add}>{t.add}</button>}
    </div>
    <p className="definition-boundary">{t.configuredOnly}</p>
    {!canViewPolicies ? <p>{t.policyDenied}</p> : <div className="actions">
      <button type="button" disabled={busy} onClick={() => void load(false)}>{t.reloadPolicies}</button>
      {cursor && <button type="button" disabled={busy} onClick={() => void load(true)}>{t.morePolicies}</button>}
    </div>}
    {error && <p role="status">{t.policyError}</p>}
    {canViewPolicies && !published.length && <p>{t.noPolicies}</p>}
    {!values.length && <p>{t.noRequirements}</p>}
    <ol className="definition-fields">{values.map((value, index) => {
      const policy = policies.find(item => item.id === value.file_policy_id);
      return <li key={index}>
        <div className="definition-field-head"><strong>{index + 1}. {locale === "ta" ? value.label_ta || value.key : value.label_en || value.key}</strong>
          {!disabled && <div><button type="button" aria-label={t.moveUp} disabled={locked || index === 0} onClick={() => move(index, -1)}>↑</button><button type="button" aria-label={t.moveDown} disabled={locked || index === values.length - 1} onClick={() => move(index, 1)}>↓</button><button type="button" disabled={locked} onClick={() => onChange(values.filter((_, position) => position !== index))}>{t.remove}</button></div>}
        </div>
        <fieldset disabled={locked}><div className="definition-field-grid">
          <label>{t.key}<input required maxLength={80} pattern="[a-z][a-z0-9_]*" value={value.key} onChange={event => update(index, { key: event.target.value })} /></label>
          <label>{t.policy}<select required value={value.file_policy_id} onChange={event => update(index, { file_policy_id: event.target.value })}><option value="">{t.choose}</option>{value.file_policy_id && !published.some(item => item.id === value.file_policy_id) && <option value={value.file_policy_id}>{t.savedPolicy}: {value.file_policy_id}</option>}{published.map(item => <option key={item.id} value={item.id}>{item.name} · {t.edition} {item.edition}</option>)}</select></label>
          <label>{t.labelEn}<input lang="en" required maxLength={200} value={value.label_en} onChange={event => update(index, { label_en: event.target.value })} /></label>
          <label>{t.labelTa}<input lang="ta" required maxLength={200} value={value.label_ta} onChange={event => update(index, { label_ta: event.target.value })} /></label>
          <label>{t.instructionsEn}<textarea lang="en" required maxLength={2000} value={value.instructions_en} onChange={event => update(index, { instructions_en: event.target.value })} /></label>
          <label>{t.instructionsTa}<textarea lang="ta" required maxLength={2000} value={value.instructions_ta} onChange={event => update(index, { instructions_ta: event.target.value })} /></label>
          <label>{t.minimum}<input required type="number" min={0} max={policy?.max_files ?? 100} step={1} value={value.min_files} onChange={event => update(index, { min_files: event.target.value })} /></label>
          <label>{t.maximum}<input required type="number" min={1} max={policy?.max_files ?? 100} step={1} value={value.max_files} onChange={event => update(index, { max_files: event.target.value })} /></label>
        </div></fieldset>
        <p>{t.countHelp}</p>
        {policy && <dl><dt>{t.formats}</dt><dd>{policy.allowed_mime_types.join(", ")}</dd><dt>{t.maxBytes}</dt><dd>{policy.max_file_bytes}</dd><dt>{t.policyMaximum}</dt><dd>{policy.max_files}</dd><dt>{t.notice}</dt><dd lang={locale}>{locale === "ta" ? policy.notice_ta : policy.notice_en}</dd></dl>}
      </li>;
    })}</ol>
  </section>;
}
