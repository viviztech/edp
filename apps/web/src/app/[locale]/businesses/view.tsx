"use client";

import { useEffect, useRef, useState } from "react";
import type { components } from "../../../lib/api-contracts";
import { businessValue } from "../../../lib/business-values";

type Profile = components["schemas"]["app__modules__businesses__schemas__ProfileView"];
type MyBusinesses = components["schemas"]["MyBusinesses"];
type Entry = MyBusinesses["entries"][number];
type CreateProfile = components["schemas"]["CreateProfile"];
type UpdateProfile = components["schemas"]["UpdateProfile"];
type OutcomeCreate = components["schemas"]["OutcomeCreate"];
type OutcomeView = components["schemas"]["OutcomeView"];
type Fields = Omit<CreateProfile, "enrollment_id">;
const initial: Fields = { name: "", sector: "", products_services: "", stage: "idea",
  registration_info: null, started_on: null, team_size: 1, investment_band: "none",
  funding_status: "none", revenue_band: "none", support_needs: null, public_opt_in: false };

// Project at runtime: API responses also contain immutable history and server metadata.
function editableFields(source: Fields): Fields {
  return {
    name: source.name, sector: source.sector, products_services: source.products_services,
    stage: source.stage, registration_info: source.registration_info ?? null,
    started_on: source.started_on ?? null, team_size: source.team_size,
    investment_band: source.investment_band, funding_status: source.funding_status,
    revenue_band: source.revenue_band, support_needs: source.support_needs ?? null,
    public_opt_in: source.public_opt_in,
  };
}
const copy = {
  en: { title: "My business", intro: "Record your business and report progress at each follow-up.",
    name: "Business name", sector: "Sector", products: "Products and services", stage: "Stage",
    registration: "Registration details", started: "Start date", team: "Team size",
    investment: "Investment", funding: "Funding status", revenue: "Monthly revenue",
    support: "Support needed", public: "I may want a public listing in the future",
    save: "Save business", followups: "Follow-ups", report: "Report outcome", active: "Business active",
    jobs: "Jobs created", challenges: "Challenges", requested: "Support requested",
    interventions: "Mentor interventions", outcomes: "Outcomes", startedBusiness: "Business started",
    error: "Could not save. Please retry.", saved: "Saved.", empty: "No enrollment is available.",
    history: "Profile versions", loading: "Loading..." },
  ta: { title: "எனது தொழில்", intro: "உங்கள் தொழிலையும் அதன் முன்னேற்றத்தையும் பதிவு செய்யுங்கள்.",
    name: "தொழில் பெயர்", sector: "துறை", products: "பொருட்கள் மற்றும் சேவைகள்", stage: "நிலை",
    registration: "பதிவு விவரம்", started: "தொடங்கிய தேதி", team: "குழு அளவு",
    investment: "முதலீடு", funding: "நிதி நிலை", revenue: "மாத வருவாய்",
    support: "தேவையான ஆதரவு", public: "எதிர்காலத்தில் பொதுப் பட்டியலில் சேர விரும்புகிறேன்",
    save: "தொழிலைச் சேமி", followups: "பின்தொடர்வுகள்", report: "முடிவைப் பதிவு செய்",
    active: "தொழில் செயல்பாட்டில் உள்ளது", jobs: "உருவாக்கப்பட்ட வேலைகள்",
    challenges: "சவால்கள்", requested: "கோரிய ஆதரவு", interventions: "வழிகாட்டி உதவி",
    outcomes: "முடிவுகள்", startedBusiness: "தொழில் தொடங்கப்பட்டது",
    error: "சேமிக்க முடியவில்லை. மீண்டும் முயற்சிக்கவும்.", saved: "சேமிக்கப்பட்டது.",
    empty: "சேர்க்கை இல்லை.", history: "தொழில் பதிவின் பதிப்புகள்", loading: "ஏற்றப்படுகிறது..." },
} as const;

const recovery = {
  en: { refresh: "Refresh saved progress", paused: "Refresh saved progress before another save. Your input is kept.",
    latest: "Latest saved business", refreshDone: "Latest progress loaded. Your input is kept; compare it before saving.",
    refreshError: "Could not refresh. Your input is kept.", early: "You may report early. The scheduled date stays unchanged." },
  ta: { refresh: "சேமித்த முன்னேற்றத்தைப் புதுப்பி", paused: "மீண்டும் சேமிக்கும் முன் முன்னேற்றத்தைப் புதுப்பிக்கவும். உங்கள் உள்ளீடு பாதுகாக்கப்பட்டுள்ளது.",
    latest: "கடைசியாகச் சேமித்த தொழில்", refreshDone: "முன்னேற்றம் புதுப்பிக்கப்பட்டது. சேமிக்கும் முன் உங்கள் உள்ளீட்டை ஒப்பிடவும்.",
    refreshError: "புதுப்பிக்க முடியவில்லை. உங்கள் உள்ளீடு பாதுகாக்கப்பட்டுள்ளது.", early: "முன்கூட்டியே அறிக்கை அளிக்கலாம். திட்டமிட்ட தேதி மாறாது." },
} as const;

function initialReport(): OutcomeCreate {
  return { reported_on: new Date().toISOString().slice(0, 10), business_started: false,
    business_active: false, jobs_created: 0, funding_band: "none", revenue_band: "none",
    challenges: "", support_requested: "", mentor_interventions: "", outcomes: "" };
}

async function post(url: string, body: CreateProfile | UpdateProfile | OutcomeCreate): Promise<Response> {
  const csrf = await fetch("/api/session/csrf", { cache: "no-store" });
  if (!csrf.ok) throw new Error("csrf_failed");
  const { csrf_token } = await csrf.json() as { csrf_token: string };
  return fetch(url, { method: "POST", headers: { "Content-Type": "application/json", "x-csrf-token": csrf_token },
    body: JSON.stringify(body) });
}

function Editor({ entry, org, locale }: { entry: Entry; org: string; locale: "en" | "ta" }) {
  const t = copy[locale];
  const [profile, setProfile] = useState(entry.profile);
  const [fields, setFields] = useState<Fields>(() => editableFields(entry.profile ?? initial));
  const [busy, setBusy] = useState(false);
  const writing = useRef(false);
  const [paused, setPaused] = useState(false);
  const [message, setMessage] = useState("");
  const [reports, setReports] = useState<Record<string, OutcomeCreate>>({});
  const r = recovery[locale];
  const dirty = JSON.stringify(editableFields(fields)) !== JSON.stringify(editableFields(profile ?? initial)) ||
    Object.keys(reports).some((id) => !profile?.follow_ups.find((item) => item.id === id)?.outcome);
  useEffect(() => {
    const guard = (event: BeforeUnloadEvent) => { if (dirty || busy) { event.preventDefault(); event.returnValue = ""; } };
    window.addEventListener("beforeunload", guard);
    return () => window.removeEventListener("beforeunload", guard);
  }, [dirty, busy]);
  const setReport = (id: string, patch: Partial<OutcomeCreate>) => setReports((old) => ({
    ...old, [id]: { ...(old[id] ?? initialReport()), ...patch },
  }));
  const set = <Key extends keyof Fields>(key: Key, value: Fields[Key]) =>
    setFields((old) => ({ ...old, [key]: value }));
  async function save() {
    if (writing.current || paused) return;
    writing.current = true;
    setBusy(true); setMessage("");
    try {
      const base = `/api/businesses/organizations/${org}/profiles`;
      const writable = editableFields(fields);
      const body: CreateProfile | UpdateProfile = profile
        ? { ...writable, expected_version: profile.version }
        : { ...writable, enrollment_id: entry.enrollment_id };
      const response = await post(profile ? `${base}/${profile.id}/update` : base, body);
      if (!response.ok) throw new Error("save_failed");
      const saved = await response.json() as Profile;
      setProfile(saved); setFields(editableFields(saved)); setMessage(t.saved);
    } catch { setPaused(true); setMessage(r.paused); } finally { writing.current = false; setBusy(false); }
  }
  async function submit(id: string) {
    if (writing.current || paused) return;
    writing.current = true;
    setBusy(true); setMessage("");
    try {
      const response = await post(`/api/businesses/organizations/${org}/follow-ups/${id}/outcome`, reports[id] ?? initialReport());
      if (!response.ok) throw new Error("report_failed");
      const outcome = await response.json() as OutcomeView;
      setProfile((old) => old ? { ...old, follow_ups: old.follow_ups.map((item) =>
        item.id === id ? { ...item, status: "completed", outcome } : item) } : old);
      setMessage(t.saved);
    } catch { setPaused(true); setMessage(r.paused); } finally { writing.current = false; setBusy(false); }
  }
  async function refresh() {
    if (writing.current) return;
    writing.current = true; setBusy(true);
    try {
      const loaded = await fetch(`/api/businesses/organizations/${org}/mine`, { cache: "no-store" });
      if (!loaded.ok) throw new Error();
      const data = await loaded.json() as MyBusinesses;
      const current = data.entries.find((item) => item.enrollment_id === entry.enrollment_id);
      if (!current) throw new Error();
      setProfile(current.profile); setPaused(false); setMessage(r.refreshDone);
    } catch { setMessage(r.refreshError); } finally { writing.current = false; setBusy(false); }
  }
  return <section className="program-panel"><h2>{t.title}</h2><p role="status">{message}</p>
    <button type="button" disabled={busy} onClick={() => void refresh()}>{r.refresh}</button>
    {profile && <details><summary>{r.latest} · v{profile.version}</summary><p>{profile.name}</p><p>{profile.support_needs}</p></details>}
    <fieldset disabled={busy}>
    <div className="program-grid">
      <label>{t.name}<input required maxLength={160} value={fields.name} onChange={(e) => set("name", e.target.value)} /></label>
      <label>{t.sector}<input required maxLength={120} value={fields.sector} onChange={(e) => set("sector", e.target.value)} /></label>
      <label>{t.products}<textarea required maxLength={4000} value={fields.products_services} onChange={(e) => set("products_services", e.target.value)} /></label>
      <label>{t.stage}<select value={fields.stage} onChange={(e) => set("stage", e.target.value as Fields["stage"])}>
        {["idea", "starting", "operating", "paused", "closed"].map((v) => <option key={v} value={v}>{businessValue(locale, v)}</option>)}
      </select></label>
      <label>{t.registration}<input maxLength={240} value={fields.registration_info ?? ""} onChange={(e) => set("registration_info", e.target.value || null)} /></label>
      <label>{t.started}<input type="date" value={fields.started_on ?? ""} onChange={(e) => set("started_on", e.target.value || null)} /></label>
      <label>{t.team}<input type="number" min="0" max="100000" value={fields.team_size} onChange={(e) => set("team_size", Number(e.target.value))} /></label>
      <label>{t.investment}<select value={fields.investment_band} onChange={(e) => set("investment_band", e.target.value as Fields["investment_band"])}>
        {["none", "under_1l", "1l_to_5l", "5l_to_25l", "over_25l", "undisclosed"].map((v) => <option key={v} value={v}>{businessValue(locale, v)}</option>)}</select></label>
      <label>{t.funding}<select value={fields.funding_status} onChange={(e) => set("funding_status", e.target.value as Fields["funding_status"])}>
        {["none", "seeking", "applied", "approved", "disbursed"].map((v) => <option key={v} value={v}>{businessValue(locale, v)}</option>)}</select></label>
      <label>{t.revenue}<select value={fields.revenue_band} onChange={(e) => set("revenue_band", e.target.value as Fields["revenue_band"])}>
        {["none", "under_10k", "10k_to_50k", "50k_to_2l", "over_2l", "undisclosed"].map((v) => <option key={v} value={v}>{businessValue(locale, v)}</option>)}</select></label>
      <label>{t.support}<textarea maxLength={4000} value={fields.support_needs ?? ""} onChange={(e) => set("support_needs", e.target.value || null)} /></label>
    </div>
    <label><input type="checkbox" checked={fields.public_opt_in} onChange={(e) => set("public_opt_in", e.target.checked)} /> {t.public}</label>
    <p><button type="button" disabled={busy || paused || fields.name.trim().length < 2 || fields.sector.trim().length < 2 || !fields.products_services.trim()}
      onClick={() => void save()}>{t.save}</button></p>
    </fieldset>
    {profile && <><h3>{t.followups}</h3><p>{r.early}</p><ol className="program-list">{profile.follow_ups.map((item) => {
      const report = reports[item.id] ?? initialReport();
      return <li key={item.id}><strong>{item.due_on}</strong> · {businessValue(locale, item.status)}
        {item.outcome ? <p>{t.jobs}: {item.outcome.jobs_created}</p> : <details><summary>{t.report}</summary>
          <fieldset disabled={busy}>
          <div className="program-grid"><label>{t.startedBusiness}<input type="checkbox" checked={report.business_started}
            onChange={(e) => setReport(item.id, { business_started: e.target.checked, business_active: e.target.checked ? report.business_active : false })} /></label>
          <label>{t.active}<input type="checkbox" checked={report.business_active} disabled={!report.business_started}
            onChange={(e) => setReport(item.id, { business_active: e.target.checked })} /></label>
          <label>{t.jobs}<input type="number" min="0" max="100000" value={report.jobs_created}
            onChange={(e) => setReport(item.id, { jobs_created: Number(e.target.value) })} /></label>
          <label>{t.funding}<select value={report.funding_band} onChange={(e) => setReport(item.id, { funding_band: e.target.value as OutcomeCreate["funding_band"] })}>
            {["none", "under_1l", "1l_to_5l", "5l_to_25l", "over_25l", "undisclosed"].map((v) => <option key={v} value={v}>{businessValue(locale, v)}</option>)}</select></label>
          <label>{t.revenue}<select value={report.revenue_band} onChange={(e) => setReport(item.id, { revenue_band: e.target.value as OutcomeCreate["revenue_band"] })}>
            {["none", "under_10k", "10k_to_50k", "50k_to_2l", "over_2l", "undisclosed"].map((v) => <option key={v} value={v}>{businessValue(locale, v)}</option>)}</select></label>
          {([ ["challenges", t.challenges], ["support_requested", t.requested], ["mentor_interventions", t.interventions], ["outcomes", t.outcomes] ] as const).map(([key, label]) =>
            <label key={key}>{label}<textarea maxLength={4000} value={report[key] ?? ""}
              onChange={(e) => setReport(item.id, { [key]: e.target.value })} /></label>)}</div>
          <button type="button" disabled={busy || paused} onClick={() => void submit(item.id)}>{t.report}</button>
          </fieldset>
        </details>}</li>; })}</ol>
      <details><summary>{t.history}</summary><ol>{profile.revisions.map((item) =>
        <li key={item.id}>v{item.version} · {new Date(item.created_at).toLocaleString(locale)}</li>)}</ol></details>
    </>}
  </section>;
}

export default function BusinessTracking({ org, locale }: { org: string; locale: "en" | "ta" }) {
  const t = copy[locale];
  const [entries, setEntries] = useState<Entry[]>([]);
  const [message, setMessage] = useState<string>(t.loading);
  useEffect(() => { let active = true; void fetch(`/api/businesses/organizations/${org}/mine`, { cache: "no-store" })
    .then(async (response) => { if (!response.ok) throw new Error(); return response.json() as Promise<MyBusinesses>; })
    .then((data) => { if (active) { setEntries(data.entries); setMessage(""); } })
    .catch(() => { if (active) setMessage(t.error); });
    return () => { active = false; }; }, [org, t.error]);
  return <><header className="program-heading"><div>
    <h1>{t.title}</h1><p>{t.intro}</p></div></header><p role="status">{message}</p>
    {!message && !entries.length && <p>{t.empty}</p>}
    {entries.map((entry) => <Editor key={entry.enrollment_id} entry={entry} org={org} locale={locale} />)}</>;
}
