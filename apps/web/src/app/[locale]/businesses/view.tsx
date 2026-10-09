"use client";

import { useEffect, useState } from "react";

type Profile = {
  id: string; enrollment_id: string; version: number; name: string; sector: string;
  products_services: string; stage: string; registration_info: string | null;
  started_on: string | null; team_size: number; investment_band: string;
  funding_status: string; revenue_band: string; support_needs: string | null;
  public_opt_in: boolean;
  revisions: { id: string; version: number; created_at: string }[];
  follow_ups: { id: string; due_on: string; offset_days: number; status: string;
    outcome: { jobs_created: number; reported_on: string } | null }[];
};
type Entry = { enrollment_id: string; program_id: string; profile: Profile | null };
type Fields = Omit<Profile, "id" | "enrollment_id" | "version" | "revisions" | "follow_ups">;
const initial: Fields = { name: "", sector: "", products_services: "", stage: "idea",
  registration_info: null, started_on: null, team_size: 1, investment_band: "none",
  funding_status: "none", revenue_band: "none", support_needs: null, public_opt_in: false };
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

async function post(url: string, body: object): Promise<Response> {
  const csrf = await fetch("/api/session/csrf", { cache: "no-store" });
  if (!csrf.ok) throw new Error("csrf_failed");
  const { csrf_token } = await csrf.json() as { csrf_token: string };
  return fetch(url, { method: "POST", headers: { "Content-Type": "application/json", "x-csrf-token": csrf_token },
    body: JSON.stringify(body) });
}

function Editor({ entry, org, locale }: { entry: Entry; org: string; locale: "en" | "ta" }) {
  const t = copy[locale];
  const [profile, setProfile] = useState(entry.profile);
  const [fields, setFields] = useState<Fields>(entry.profile ?? initial);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [report, setReport] = useState({ reported_on: new Date().toISOString().slice(0, 10),
    business_started: false, business_active: false, jobs_created: 0, funding_band: "none",
    revenue_band: "none", challenges: "", support_requested: "", mentor_interventions: "", outcomes: "" });
  const set = (key: keyof Fields, value: string | number | boolean | null) =>
    setFields((old) => ({ ...old, [key]: value }));
  async function save() {
    setBusy(true); setMessage("");
    try {
      const base = `/api/businesses/organizations/${org}/profiles`;
      const response = await post(profile ? `${base}/${profile.id}/update` : base,
        profile ? { ...fields, expected_version: profile.version } : { ...fields, enrollment_id: entry.enrollment_id });
      if (!response.ok) throw new Error("save_failed");
      setProfile(await response.json() as Profile); setMessage(t.saved);
    } catch { setMessage(t.error); } finally { setBusy(false); }
  }
  async function submit(id: string) {
    setBusy(true); setMessage("");
    try {
      const response = await post(`/api/businesses/organizations/${org}/follow-ups/${id}/outcome`, report);
      if (!response.ok) throw new Error("report_failed");
      const loaded = await fetch(`/api/businesses/organizations/${org}/mine`, { cache: "no-store" });
      if (!loaded.ok) throw new Error("reload_failed");
      const data = await loaded.json() as { entries: Entry[] };
      setProfile(data.entries.find((item) => item.enrollment_id === entry.enrollment_id)?.profile ?? null);
      setMessage(t.saved);
    } catch { setMessage(t.error); } finally { setBusy(false); }
  }
  return <section className="program-panel"><h2>{t.title}</h2><p role="status">{message}</p>
    <div className="program-grid">
      <label>{t.name}<input required maxLength={160} value={fields.name} onChange={(e) => set("name", e.target.value)} /></label>
      <label>{t.sector}<input required maxLength={120} value={fields.sector} onChange={(e) => set("sector", e.target.value)} /></label>
      <label>{t.products}<textarea required maxLength={4000} value={fields.products_services} onChange={(e) => set("products_services", e.target.value)} /></label>
      <label>{t.stage}<select value={fields.stage} onChange={(e) => set("stage", e.target.value)}>
        {["idea", "starting", "operating", "paused", "closed"].map((v) => <option key={v}>{v}</option>)}
      </select></label>
      <label>{t.registration}<input maxLength={240} value={fields.registration_info ?? ""} onChange={(e) => set("registration_info", e.target.value || null)} /></label>
      <label>{t.started}<input type="date" value={fields.started_on ?? ""} onChange={(e) => set("started_on", e.target.value || null)} /></label>
      <label>{t.team}<input type="number" min="0" max="100000" value={fields.team_size} onChange={(e) => set("team_size", Number(e.target.value))} /></label>
      <label>{t.investment}<select value={fields.investment_band} onChange={(e) => set("investment_band", e.target.value)}>
        {["none", "under_1l", "1l_to_5l", "5l_to_25l", "over_25l", "undisclosed"].map((v) => <option key={v}>{v}</option>)}</select></label>
      <label>{t.funding}<select value={fields.funding_status} onChange={(e) => set("funding_status", e.target.value)}>
        {["none", "seeking", "applied", "approved", "disbursed"].map((v) => <option key={v}>{v}</option>)}</select></label>
      <label>{t.revenue}<select value={fields.revenue_band} onChange={(e) => set("revenue_band", e.target.value)}>
        {["none", "under_10k", "10k_to_50k", "50k_to_2l", "over_2l", "undisclosed"].map((v) => <option key={v}>{v}</option>)}</select></label>
      <label>{t.support}<textarea maxLength={4000} value={fields.support_needs ?? ""} onChange={(e) => set("support_needs", e.target.value || null)} /></label>
    </div>
    <label><input type="checkbox" checked={fields.public_opt_in} onChange={(e) => set("public_opt_in", e.target.checked)} /> {t.public}</label>
    <p><button type="button" disabled={busy || fields.name.trim().length < 2 || fields.sector.trim().length < 2 || !fields.products_services.trim()}
      onClick={() => void save()}>{t.save}</button></p>
    {profile && <><h3>{t.followups}</h3><ol className="program-list">{profile.follow_ups.map((item) =>
      <li key={item.id}><strong>{item.due_on}</strong> · {item.status}
        {item.outcome ? <p>{t.jobs}: {item.outcome.jobs_created}</p> : <details><summary>{t.report}</summary>
          <div className="program-grid"><label>{t.startedBusiness}<input type="checkbox" checked={report.business_started}
            onChange={(e) => setReport((old) => ({ ...old, business_started: e.target.checked, business_active: e.target.checked ? old.business_active : false }))} /></label>
          <label>{t.active}<input type="checkbox" checked={report.business_active} disabled={!report.business_started}
            onChange={(e) => setReport((old) => ({ ...old, business_active: e.target.checked }))} /></label>
          <label>{t.jobs}<input type="number" min="0" max="100000" value={report.jobs_created}
            onChange={(e) => setReport((old) => ({ ...old, jobs_created: Number(e.target.value) }))} /></label>
          <label>{t.funding}<select value={report.funding_band} onChange={(e) => setReport((old) => ({ ...old, funding_band: e.target.value }))}>
            {["none", "under_1l", "1l_to_5l", "5l_to_25l", "over_25l", "undisclosed"].map((v) => <option key={v}>{v}</option>)}</select></label>
          <label>{t.revenue}<select value={report.revenue_band} onChange={(e) => setReport((old) => ({ ...old, revenue_band: e.target.value }))}>
            {["none", "under_10k", "10k_to_50k", "50k_to_2l", "over_2l", "undisclosed"].map((v) => <option key={v}>{v}</option>)}</select></label>
          {([ ["challenges", t.challenges], ["support_requested", t.requested], ["mentor_interventions", t.interventions], ["outcomes", t.outcomes] ] as const).map(([key, label]) =>
            <label key={key}>{label}<textarea maxLength={4000} value={report[key]}
              onChange={(e) => setReport((old) => ({ ...old, [key]: e.target.value }))} /></label>)}</div>
          <button type="button" disabled={busy} onClick={() => void submit(item.id)}>{t.report}</button>
        </details>}</li>)}</ol>
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
    .then(async (response) => { if (!response.ok) throw new Error(); return response.json() as Promise<{ entries: Entry[] }>; })
    .then((data) => { if (active) { setEntries(data.entries); setMessage(""); } })
    .catch(() => { if (active) setMessage(t.error); });
    return () => { active = false; }; }, [org, t.error]);
  return <><header className="program-heading"><div><p className="eyebrow">B02</p>
    <h1>{t.title}</h1><p>{t.intro}</p></div></header><p role="status">{message}</p>
    {!message && !entries.length && <p>{t.empty}</p>}
    {entries.map((entry) => <Editor key={entry.enrollment_id} entry={entry} org={org} locale={locale} />)}</>;
}
