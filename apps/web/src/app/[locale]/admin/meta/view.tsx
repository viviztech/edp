"use client";

import { useCallback, useEffect, useState } from "react";
import type { components } from "../../../../lib/api-contracts";
import { metaMessages, type MetaLocale } from "../../../../lib/meta-messages";

type Integration = components["schemas"]["IntegrationView"];
type Mapping = components["schemas"]["MappingView"];
type Event = components["schemas"]["EventView"];
type Health = components["schemas"]["HealthView"];
type Page<T> = { items: T[]; next_cursor?: string | null };

const emptyIntegration = { name: "", page_id: "", access_token: "", app_secret: "", verify_token: "" };
const emptyMapping = { form_id: "", name: "", campaign: "", nameField: "full_name", emailField: "email", phoneField: "phone" };
const emptyRotation = { access_token: "", app_secret: "", verify_token: "" };

export default function MetaWorkspace({ org, permissions, locale }: {
  org: string; permissions: string[]; locale: MetaLocale;
}) {
  const text = metaMessages[locale];
  const root = `/api/meta/organizations/${org}`;
  const canManage = permissions.includes("meta.integration.manage");
  const canReplay = permissions.includes("meta.integration.replay");
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [mappings, setMappings] = useState<Mapping[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [draft, setDraft] = useState(emptyIntegration);
  const [mappingDraft, setMappingDraft] = useState(emptyMapping);
  const [mappingId, setMappingId] = useState("");
  const [rotation, setRotation] = useState(emptyRotation);
  const [editName, setEditName] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const selected = integrations.find((item) => item.id === selectedId) ?? null;
  const selectedMapping = mappings.find((item) => item.id === mappingId) ?? null;

  const api = useCallback(async <T,>(path: string, method = "GET", data?: unknown): Promise<T> => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (method !== "GET") {
      const response = await fetch("/api/session/csrf", { cache: "no-store" });
      if (!response.ok) throw new Error(text.error);
      headers["x-csrf-token"] = (await response.json()).csrf_token;
    }
    const response = await fetch(path, {
      method, headers, body: data === undefined ? undefined : JSON.stringify(data), cache: "no-store",
    });
    if (!response.ok) throw new Error(response.status === 409 ? text.conflict : text.error);
    return response.json();
  }, [text.conflict, text.error]);

  const loadOverview = useCallback(async () => {
    const [connections, deliveries, pulse] = await Promise.all([
      api<Page<Integration>>(`${root}/integrations`),
      api<Page<Event>>(`${root}/events`),
      api<Health>(`${root}/health`),
    ]);
    setIntegrations(connections.items);
    setEvents(deliveries.items);
    setCursor(deliveries.next_cursor ?? null);
    setHealth(pulse);
    setSelectedId((current) => current || connections.items[0]?.id || "");
  }, [api, root]);

  useEffect(() => {
    let active = true;
    Promise.all([
      api<Page<Integration>>(`${root}/integrations`),
      api<Page<Event>>(`${root}/events`),
      api<Health>(`${root}/health`),
    ]).then(([connections, deliveries, pulse]) => {
      if (!active) return;
      setIntegrations(connections.items);
      setEvents(deliveries.items);
      setCursor(deliveries.next_cursor ?? null);
      setHealth(pulse);
      setSelectedId(connections.items[0]?.id ?? "");
    }).catch(() => { if (active) setMessage(text.error); });
    return () => { active = false; };
  }, [api, root, text.error]);

  useEffect(() => {
    let active = true;
    if (!selectedId) return;
    api<Page<Mapping>>(`${root}/integrations/${selectedId}/mappings`)
      .then((result) => { if (active) setMappings(result.items); })
      .catch(() => { if (active) setMessage(text.error); });
    return () => { active = false; };
  }, [api, root, selectedId, text.error]);

  async function run(work: () => Promise<void>) {
    setBusy(true);
    setMessage("");
    try { await work(); setMessage(text.saved); }
    catch (error) { setMessage(error instanceof Error ? error.message : text.error); }
    finally { setBusy(false); }
  }

  function replaceIntegration(item: Integration) {
    setIntegrations((current) => current.map((entry) => entry.id === item.id ? item : entry));
  }

  function chooseMapping(item: Mapping) {
    const source = (target: string) =>
      Object.entries(item.field_mapping).find(([, value]) => value === target)?.[0] ?? "";
    setMappingId(item.id);
    setMappingDraft({
      form_id: item.form_id, name: item.name, campaign: item.campaign,
      nameField: source("name"), emailField: source("email"), phoneField: source("phone"),
    });
  }

  function fields() {
    return Object.fromEntries(
      [
        [mappingDraft.nameField.trim(), "name"],
        [mappingDraft.emailField.trim(), "email"],
        [mappingDraft.phoneField.trim(), "phone"],
      ].filter(([source]) => source)
    );
  }

  return <div className="meta-workspace" aria-busy={busy}>
    <p role="status" className="meta-message">{busy ? text.loading : message}</p>
    <section className="meta-pulse" aria-label={text.health}>
      <div><span>{text.active}</span><strong>{health?.active_integrations ?? "—"}</strong></div>
      <div><span>{text.queued}</span><strong>{health?.queued ?? "—"}</strong></div>
      <div><span>{text.retrying}</span><strong>{health?.retrying ?? "—"}</strong></div>
      <div><span>{text.processing}</span><strong>{health?.processing ?? "—"}</strong></div>
      <div className="meta-pulse-alert"><span>{text.failed}</span><strong>{health?.failed ?? "—"}</strong></div>
      <div><span>{text.completed}</span><strong>{health?.completed ?? "—"}</strong></div>
      <button disabled={busy} onClick={() => run(loadOverview)}>{text.refresh}</button>
    </section>
    <div className="meta-grid">
      <aside className="meta-rail">
        <h2>{text.integrations}</h2>
        {integrations.length === 0 ? <p>{text.noConnection}</p> : <ul className="meta-connections">{integrations.map((item) =>
          <li key={item.id}><button aria-pressed={selectedId === item.id} onClick={() => { setSelectedId(item.id); setMappingId(""); setMappings([]); setEditName(item.name); }}><strong>{item.name}</strong><small>{item.page_id}</small><span className={`meta-state meta-state-${item.status}`}>{text[item.status]}</span></button></li>
        )}</ul>}
        {canManage ? <form className="meta-form" onSubmit={(event) => { event.preventDefault(); run(async () => {
          const item = await api<Integration>(`${root}/integrations`, "POST", draft);
          setIntegrations((current) => [...current, item]);
          setSelectedId(item.id); setDraft(emptyIntegration); setEditName(item.name);
          await loadOverview();
        }); }}>
          <h3>{text.newIntegration}</h3>
          <label>{text.name}<input required maxLength={120} value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} /></label>
          <label>{text.pageId}<input required maxLength={80} value={draft.page_id} onChange={(event) => setDraft({ ...draft, page_id: event.target.value })} /></label>
          <label>{text.accessToken}<input required type="password" autoComplete="off" minLength={20} value={draft.access_token} onChange={(event) => setDraft({ ...draft, access_token: event.target.value })} /></label>
          <label>{text.appSecret}<input required type="password" autoComplete="off" minLength={16} value={draft.app_secret} onChange={(event) => setDraft({ ...draft, app_secret: event.target.value })} /></label>
          <label>{text.verifyToken}<input required type="password" autoComplete="off" minLength={24} value={draft.verify_token} onChange={(event) => setDraft({ ...draft, verify_token: event.target.value })} /></label>
          <button disabled={busy}>{text.create}</button>
        </form> : null}
      </aside>
      <div className="meta-detail">
        {selected ? <>
          <header className="meta-record"><div><p className="eyebrow">{selected.page_id}</p><h2>{selected.name}</h2></div><span className={`meta-state meta-state-${selected.status}`}>{text[selected.status]}</span></header>
          {canManage ? <div className="meta-panels">
            <section className="meta-panel"><h3>{text.configuration}</h3>
              <form className="meta-form" onSubmit={(event) => { event.preventDefault(); run(async () => {
                replaceIntegration(await api<Integration>(`${root}/integrations/${selected.id}`, "PATCH", {
                  name: editName || selected.name, status: selected.status, expected_version: selected.version,
                }));
              }); }}>
                <label>{text.name}<input maxLength={120} value={editName || selected.name} onChange={(event) => setEditName(event.target.value)} /></label>
                <button disabled={busy}>{text.save}</button>
              </form>
              <button className="meta-secondary" disabled={busy} onClick={() => run(async () => {
                replaceIntegration(await api<Integration>(`${root}/integrations/${selected.id}`, "PATCH", {
                  name: selected.name, status: selected.status === "active" ? "disabled" : "active",
                  expected_version: selected.version,
                }));
                await loadOverview();
              })}>{selected.status === "active" ? text.pause : text.resume}</button>
            </section>
            <section className="meta-panel"><h3>{text.rotate}</h3><p>{text.rotateHint}</p>
              <form className="meta-form" onSubmit={(event) => { event.preventDefault(); run(async () => {
                replaceIntegration(await api<Integration>(`${root}/integrations/${selected.id}/rotate`, "POST", {
                  expected_version: selected.version,
                  access_token: rotation.access_token || null,
                  app_secret: rotation.app_secret || null,
                  verify_token: rotation.verify_token || null,
                }));
                setRotation(emptyRotation);
              }); }}>
                <label>{text.accessToken}<input type="password" autoComplete="off" minLength={20} value={rotation.access_token} onChange={(event) => setRotation({ ...rotation, access_token: event.target.value })} /></label>
                <label>{text.appSecret}<input type="password" autoComplete="off" minLength={16} value={rotation.app_secret} onChange={(event) => setRotation({ ...rotation, app_secret: event.target.value })} /></label>
                <label>{text.verifyToken}<input type="password" autoComplete="off" minLength={24} value={rotation.verify_token} onChange={(event) => setRotation({ ...rotation, verify_token: event.target.value })} /></label>
                <button disabled={busy || !Object.values(rotation).some(Boolean)}>{text.rotate}</button>
              </form>
            </section>
          </div> : null}
          <section className="meta-panel"><h3>{text.forms}</h3>
            {mappings.length === 0 ? <p>{text.noMappings}</p> : <ul className="meta-mappings">{mappings.map((item) =>
              <li key={item.id}><button aria-pressed={mappingId === item.id} onClick={() => chooseMapping(item)}>{item.name} · {item.form_id}</button><span className={`meta-state meta-state-${item.status}`}>{text[item.status]}</span></li>
            )}</ul>}
            {canManage ? <form className="meta-form meta-mapping-form" onSubmit={(event) => { event.preventDefault(); run(async () => {
              const sources = [mappingDraft.nameField, mappingDraft.emailField, mappingDraft.phoneField].map((value) => value.trim()).filter(Boolean);
              if (new Set(sources).size !== sources.length) throw new Error(text.error);
              const data = {
                form_id: mappingDraft.form_id, name: mappingDraft.name, campaign: mappingDraft.campaign,
                field_mapping: fields(),
              };
              if (selectedMapping) {
                const updated = await api<Mapping>(`${root}/integrations/${selected.id}/mappings/${selectedMapping.id}`, "PATCH", {
                  ...data, status: selectedMapping.status, expected_version: selectedMapping.version,
                });
                setMappings((current) => current.map((item) => item.id === updated.id ? updated : item));
              } else {
                const created = await api<Mapping>(`${root}/integrations/${selected.id}/mappings`, "POST", data);
                setMappings((current) => [...current, created]);
              }
              setMappingId(""); setMappingDraft(emptyMapping);
            }); }}>
              <div className="meta-form-grid">
                <label>{text.formId}<input required maxLength={80} value={mappingDraft.form_id} onChange={(event) => setMappingDraft({ ...mappingDraft, form_id: event.target.value })} /></label>
                <label>{text.name}<input required maxLength={120} value={mappingDraft.name} onChange={(event) => setMappingDraft({ ...mappingDraft, name: event.target.value })} /></label>
                <label>{text.campaign}<input maxLength={120} value={mappingDraft.campaign} onChange={(event) => setMappingDraft({ ...mappingDraft, campaign: event.target.value })} /></label>
                <label>{text.providerName}<input required maxLength={80} value={mappingDraft.nameField} onChange={(event) => setMappingDraft({ ...mappingDraft, nameField: event.target.value })} /></label>
                <label>{text.providerEmail}<input maxLength={80} value={mappingDraft.emailField} onChange={(event) => setMappingDraft({ ...mappingDraft, emailField: event.target.value })} /></label>
                <label>{text.providerPhone}<input maxLength={80} value={mappingDraft.phoneField} onChange={(event) => setMappingDraft({ ...mappingDraft, phoneField: event.target.value })} /></label>
              </div>
              <div className="actions"><button disabled={busy}>{selectedMapping ? text.save : text.addMapping}</button>{selectedMapping ? <button type="button" onClick={() => { setMappingId(""); setMappingDraft(emptyMapping); }}>{text.cancel}</button> : null}</div>
            </form> : null}
            {selectedMapping && canManage ? <button className="meta-secondary" disabled={busy} onClick={() => run(async () => {
              const updated = await api<Mapping>(`${root}/integrations/${selected.id}/mappings/${selectedMapping.id}`, "PATCH", {
                form_id: selectedMapping.form_id, name: selectedMapping.name, campaign: selectedMapping.campaign,
                field_mapping: selectedMapping.field_mapping, expected_version: selectedMapping.version,
                status: selectedMapping.status === "active" ? "disabled" : "active",
              });
              setMappings((current) => current.map((item) => item.id === updated.id ? updated : item));
            })}>{selectedMapping.status === "active" ? text.pause : text.resume}</button> : null}
          </section>
        </> : null}
      </div>
    </div>
    <section className="meta-panel meta-events"><div className="meta-section-head"><h2>{text.events}</h2><button disabled={busy} onClick={() => run(loadOverview)}>{text.refresh}</button></div>
      {events.length === 0 ? <p>{text.noEvents}</p> : <ol>{events.map((item) =>
        <li key={item.id}><div><strong>{item.meta_lead_id}</strong><small>{item.form_id} · {new Date(item.created_at).toLocaleString(locale)}</small></div><span className={`meta-state meta-state-${item.state}`}>{text[item.state]}</span>{item.error_code ? <code>{item.error_code}</code> : null}
          {item.state === "failed" && canReplay ? <form onSubmit={(event) => { event.preventDefault(); run(async () => {
            const updated = await api<Event>(`${root}/events/${item.id}/replay`, "POST", { expected_version: item.version, reason });
            setEvents((current) => current.map((entry) => entry.id === updated.id ? updated : entry));
            setReason(""); setHealth(await api<Health>(`${root}/health`));
          }); }}><label>{text.reason}<input required maxLength={500} value={reason} onChange={(event) => setReason(event.target.value)} /></label><button disabled={busy}>{text.replay}</button></form> : null}
        </li>
      )}</ol>}
      {cursor ? <button disabled={busy} onClick={() => run(async () => {
        const page = await api<Page<Event>>(`${root}/events?cursor=${cursor}`);
        setEvents((current) => [...current, ...page.items]); setCursor(page.next_cursor ?? null);
      })}>{text.more}</button> : null}
    </section>
  </div>;
}
