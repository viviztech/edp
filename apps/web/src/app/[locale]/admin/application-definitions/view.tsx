"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { components } from "../../../../lib/api-contracts";
import { applicationAdminMessages } from "../../../../lib/application-admin-messages";

type Definition = components["schemas"]["DefinitionView"];
type FieldType = components["schemas"]["DefinitionFieldInput"]["field_type"];
type DraftField = components["schemas"]["DefinitionFieldInput"];
type DraftAcknowledgement = components["schemas"]["AcknowledgementInput"];
type Locale = "en" | "ta";

const newField = (index: number): DraftField => ({
  key: `field_${index}`, section: "general", label_en: "", label_ta: "",
  field_type: "text", required: false,
});

const newAcknowledgement = (index: number): DraftAcknowledgement => ({
  key: `acknowledgement_${index}`, kind: index === 1 ? "declaration" : "consent",
  label_en: "", label_ta: "", required: true,
});

export default function ApplicationDefinitionWorkspace({ org, locale, permissions }: {
  org: string; locale: Locale; permissions: string[];
}) {
  const text = applicationAdminMessages[locale];
  const root = `/api/application-definitions/organizations/${org}/definitions`;
  const [items, setItems] = useState<Definition[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [titleEn, setTitleEn] = useState("");
  const [titleTa, setTitleTa] = useState("");
  const [fields, setFields] = useState<DraftField[]>([newField(1)]);
  const [acknowledgements, setAcknowledgements] = useState<DraftAcknowledgement[]>([newAcknowledgement(1), newAcknowledgement(2)]);
  const [busy, setBusy] = useState(true);
  const [message, setMessage] = useState<string>(text.loading);
  const selected = useMemo(() => items.find((item) => item.id === selectedId), [items, selectedId]);
  const canCreate = permissions.includes("application.form.create");
  const canUpdate = permissions.includes("application.form.update");
  const canPublish = permissions.includes("application.form.publish");
  const editable = selectedId === "new" ? canCreate : selected?.state === "draft" && canUpdate;

  const request = useCallback(async <T,>(path: string, method = "GET", data?: unknown): Promise<T> => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (method !== "GET") {
      const tokenResponse = await fetch("/api/session/csrf", { cache: "no-store" });
      if (!tokenResponse.ok) throw new Error("service_unavailable");
      headers["x-csrf-token"] = (await tokenResponse.json()).csrf_token;
    }
    const response = await fetch(path, {
      method, headers, body: data === undefined ? undefined : JSON.stringify(data), cache: "no-store",
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body?.error?.code ?? "request_failed");
    return body as T;
  }, []);

  const edit = useCallback((item: Definition) => {
    setSelectedId(item.id); setTitleEn(item.title_en); setTitleTa(item.title_ta);
    setFields(item.fields.map((entry) => ({
      key: entry.key, section: entry.section, label_en: entry.label_en,
      label_ta: entry.label_ta, field_type: entry.field_type, required: entry.required,
    })));
    setAcknowledgements(item.acknowledgements.map((entry) => ({
      key: entry.key, kind: entry.kind, label_en: entry.label_en,
      label_ta: entry.label_ta, required: entry.required,
    })));
    setMessage("");
  }, []);

  const load = useCallback(async (preferred?: string) => {
    const result = await request<components["schemas"]["DefinitionList"]>(root);
    setItems(result.items);
    const choice = result.items.find((item) => item.id === preferred) ?? result.items[0];
    if (choice) edit(choice); else { setSelectedId(""); setMessage(text.noVersions); }
  }, [edit, request, root, text.noVersions]);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const result = await request<components["schemas"]["DefinitionList"]>(root);
        if (!active) return;
        setItems(result.items);
        if (result.items[0]) edit(result.items[0]); else setMessage(text.noVersions);
      } catch { if (active) setMessage(text.error); }
      finally { if (active) setBusy(false); }
    })();
    return () => { active = false; };
  }, [edit, request, root, text.error, text.noVersions]);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    try { await action(); }
    catch (error) {
      setMessage(error instanceof Error && error.message === "version_conflict" ? text.conflict : text.error);
    } finally { setBusy(false); }
  }

  function beginNew() {
    setSelectedId("new"); setTitleEn(""); setTitleTa(""); setFields([newField(1)]);
    setAcknowledgements([newAcknowledgement(1), newAcknowledgement(2)]); setMessage("");
  }
  function updateField(index: number, patch: Partial<DraftField>) {
    setFields((current) => current.map((item, position) => position === index ? { ...item, ...patch } : item));
  }
  function move(index: number, offset: number) {
    setFields((current) => {
      const target = index + offset;
      if (target < 0 || target >= current.length) return current;
      const next = [...current];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  function updateAcknowledgement(index: number, patch: Partial<DraftAcknowledgement>) {
    setAcknowledgements((current) => current.map((item, position) => position === index ? { ...item, ...patch } : item));
  }

  const payload = { title_en: titleEn, title_ta: titleTa, fields, acknowledgements };
  const hasDraft = items.some((item) => item.state === "draft");

  return <div className="definition-workspace" aria-busy={busy}>
    <p className="definition-message" role="status">{busy ? text.loading : message}</p>
    <div className="definition-layout">
      <aside className="definition-versions">
        <div className="definition-section-head"><h2>{text.versions}</h2>
          {canCreate ? <button type="button" disabled={busy || hasDraft} onClick={beginNew}>{text.newDefinition}</button> : null}
        </div>
        {items.length === 0 ? <p>{text.noVersions}</p> : <ol>{items.map((item) =>
          <li key={item.id}><button type="button" aria-pressed={selectedId === item.id} onClick={() => edit(item)}>
            <strong>{text.version} {item.version}</strong>
            <span className={`definition-state definition-state-${item.state}`}>{text[item.state]}</span>
            <small>{text.revision} {item.revision}</small>
          </button></li>
        )}</ol>}
      </aside>
      <section className="definition-editor">
        {!selectedId ? <p>{text.selectVersion}</p> : <>
          <header className="definition-record">
            <div><p className="eyebrow">{selectedId === "new" ? text.newDefinition : `${text.version} ${selected?.version}`}</p><h2>{titleEn || text.newDefinition}</h2></div>
            {selected ? <span className={`definition-state definition-state-${selected.state}`}>{text[selected.state]}</span> : null}
          </header>
          {selected && selected.state !== "draft" ? <p className="definition-boundary">{text.immutable}</p> : null}
          <form onSubmit={(event) => {
            event.preventDefault();
            const creating = selectedId === "new";
            run(async () => {
              const result = creating
                ? await request<Definition>(root, "POST", payload)
                : await request<Definition>(`${root}/${selectedId}`, "PATCH", { ...payload, expected_revision: selected?.revision });
              await load(result.id);
              setMessage(creating ? text.created : text.saved);
            });
          }}>
            <div className="definition-title-grid">
              <label>{text.englishTitle}<input required maxLength={160} disabled={!editable || busy} value={titleEn} onChange={(event) => setTitleEn(event.target.value)} /></label>
              <label>{text.tamilTitle}<input required maxLength={160} disabled={!editable || busy} value={titleTa} onChange={(event) => setTitleTa(event.target.value)} /></label>
            </div>
            <div className="definition-section-head"><h3>{text.fields}</h3>
              {editable ? <button type="button" disabled={busy || fields.length >= 100} onClick={() => setFields((current) => [...current, newField(current.length + 1)])}>{text.addField}</button> : null}
            </div>
            <ol className="definition-fields">{fields.map((item, index) => <li key={index}>
              <div className="definition-field-head"><strong>{index + 1}. {item.label_en || item.key}</strong>
                {editable ? <div>
                  <button type="button" aria-label={text.moveUp} disabled={busy || index === 0} onClick={() => move(index, -1)}>&uarr;</button>
                  <button type="button" aria-label={text.moveDown} disabled={busy || index === fields.length - 1} onClick={() => move(index, 1)}>&darr;</button>
                  <button type="button" disabled={busy || fields.length === 1} onClick={() => setFields((current) => current.filter((_, position) => position !== index))}>{text.remove}</button>
                </div> : null}
              </div>
              <div className="definition-field-grid">
                <label>{text.key}<input required pattern="[a-z][a-z0-9_]*" maxLength={80} disabled={!editable || busy} value={item.key} onChange={(event) => updateField(index, { key: event.target.value })} /></label>
                <label>{text.section}<input required pattern="[a-z][a-z0-9_]*" maxLength={80} disabled={!editable || busy} value={item.section} onChange={(event) => updateField(index, { section: event.target.value })} /></label>
                <label>{text.englishLabel}<input required maxLength={200} disabled={!editable || busy} value={item.label_en} onChange={(event) => updateField(index, { label_en: event.target.value })} /></label>
                <label>{text.tamilLabel}<input required maxLength={200} disabled={!editable || busy} value={item.label_ta} onChange={(event) => updateField(index, { label_ta: event.target.value })} /></label>
                <label>{text.type}<select disabled={!editable || busy} value={item.field_type} onChange={(event) => updateField(index, { field_type: event.target.value as FieldType })}>
                  {(["text", "textarea", "number", "date", "boolean"] as FieldType[]).map((type) => <option key={type} value={type}>{text[type]}</option>)}
                </select></label>
                <label className="definition-required"><input type="checkbox" disabled={!editable || busy} checked={item.required} onChange={(event) => updateField(index, { required: event.target.checked })} />{text.required}</label>
              </div>
            </li>)}</ol>
            <div className="definition-section-head"><h3>{text.acknowledgements}</h3>
              {editable ? <button type="button" disabled={busy || acknowledgements.length >= 20} onClick={() => setAcknowledgements((current) => [...current, newAcknowledgement(current.length + 1)])}>{text.addAcknowledgement}</button> : null}
            </div>
            <p className="definition-boundary">{text.publishRequirements}</p>
            <ol className="definition-fields">{acknowledgements.map((item, index) => <li key={index}>
              <div className="definition-field-head"><strong>{index + 1}. {item.label_en || item.key}</strong>{editable ? <button type="button" disabled={busy || acknowledgements.length <= 2} onClick={() => setAcknowledgements((current) => current.filter((_, position) => position !== index))}>{text.remove}</button> : null}</div>
              <div className="definition-field-grid">
                <label>{text.key}<input required pattern="[a-z][a-z0-9_]*" maxLength={80} disabled={!editable || busy} value={item.key} onChange={(event) => updateAcknowledgement(index, { key: event.target.value })} /></label>
                <label>{text.acknowledgementKind}<select disabled={!editable || busy} value={item.kind} onChange={(event) => updateAcknowledgement(index, { kind: event.target.value as DraftAcknowledgement["kind"] })}><option value="declaration">{text.declaration}</option><option value="consent">{text.consent}</option></select></label>
                <label>{text.englishLabel}<textarea required maxLength={1000} disabled={!editable || busy} value={item.label_en} onChange={(event) => updateAcknowledgement(index, { label_en: event.target.value })} /></label>
                <label>{text.tamilLabel}<textarea required maxLength={1000} disabled={!editable || busy} value={item.label_ta} onChange={(event) => updateAcknowledgement(index, { label_ta: event.target.value })} /></label>
                <label className="definition-required"><input type="checkbox" disabled={!editable || busy} checked={item.required} onChange={(event) => updateAcknowledgement(index, { required: event.target.checked })} />{text.required}</label>
              </div>
            </li>)}</ol>
            {editable ? <button className="definition-primary" disabled={busy}>{text.save}</button> : null}
          </form>
          {selected ? <div className="definition-actions">
            {selected.state !== "draft" && canCreate ? <button disabled={busy || hasDraft} onClick={() => run(async () => {
              const result = await request<Definition>(`${root}/${selected.id}/copy`, "POST", { expected_revision: selected.revision });
              await load(result.id); setMessage(text.copied);
            })}>{text.copy}</button> : null}
            {selected.state === "draft" && canPublish ? <button className="definition-publish" disabled={busy} onClick={() => {
              if (!window.confirm(text.publishing)) return;
              run(async () => {
                const result = await request<Definition>(`${root}/${selected.id}/publish`, "POST", { expected_revision: selected.revision });
                await load(result.id); setMessage(text.publishedMessage);
              });
            }}>{text.publish}</button> : selected.state === "draft" ? <p>{text.publicationRole}</p> : null}
          </div> : null}
        </>}
      </section>
    </div>
  </div>;
}
