"use client";

import { useEffect, useRef, useState } from "react";
import type { components } from "../../../../lib/api-contracts";
import { businessValue } from "../../../../lib/business-values";

type Dashboard = components["schemas"]["StaffDashboard"];
const copy = {
  en: { title: "Business follow-ups", intro: "Track participant reports and set the schedule for new profiles.",
    policy: "Follow-up days", reason: "Reason for change", save: "Save schedule",
    due: "Due", completed: "Completed", empty: "No business profiles yet.",
    error: "Could not load or save business tracking.", saved: "Schedule saved." },
  ta: { title: "தொழில் பின்தொடர்வுகள்", intro: "பங்கேற்பாளர் அறிக்கைகளையும் புதிய பதிவுகளின் கால அட்டவணையையும் நிர்வகிக்கவும்.",
    policy: "பின்தொடர்வு நாட்கள்", reason: "மாற்றத்திற்கான காரணம்", save: "அட்டவணையைச் சேமி",
    due: "நிலுவை", completed: "முடிந்தவை", empty: "தொழில் பதிவுகள் இல்லை.",
    error: "தொழில் விவரங்களை ஏற்ற அல்லது சேமிக்க முடியவில்லை.", saved: "அட்டவணை சேமிக்கப்பட்டது." },
} as const;

export default function BusinessStaff({ org, locale, canManage }: {
  org: string; locale: "en" | "ta"; canManage: boolean;
}) {
  const t = copy[locale];
  const [data, setData] = useState<Dashboard | null>(null);
  const [offsets, setOffsets] = useState("");
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const writing = useRef(false);
  const [paused, setPaused] = useState(false);
  const refreshLabel = locale === "ta" ? "சேமித்த அட்டவணையைப் புதுப்பி" : "Refresh saved schedule";
  const pausedLabel = locale === "ta" ? "மீண்டும் சேமிக்கும் முன் அட்டவணையைப் புதுப்பிக்கவும். உங்கள் உள்ளீடு பாதுகாக்கப்பட்டுள்ளது." :
    "Refresh saved schedule before another save. Your input is kept.";
  useEffect(() => { let active = true;
    void fetch(`/api/businesses/organizations/${org}/staff`, { cache: "no-store" })
      .then(async (response) => { if (!response.ok) throw new Error(); return response.json() as Promise<Dashboard>; })
      .then((loaded) => { if (active) { setData(loaded); setOffsets(loaded.policy.day_offsets.join(", ")); } })
      .catch(() => { if (active) setMessage(t.error); });
    return () => { active = false; }; }, [org, t.error]);
  async function save() {
    if (!data || writing.current || paused) return;
    writing.current = true;
    setBusy(true); setMessage("");
    try {
      const days = offsets.split(",").map((part) => Number(part.trim()));
      if (!days.length || days.some((day) => !Number.isInteger(day) || day < 1 || day > 3650) ||
          days.some((day, index) => index > 0 && day <= days[index - 1])) throw new Error();
      const csrf = await fetch("/api/session/csrf", { cache: "no-store" });
      if (!csrf.ok) throw new Error();
      const { csrf_token } = await csrf.json() as { csrf_token: string };
      const response = await fetch(`/api/businesses/organizations/${org}/policy`, {
        method: "POST", headers: { "Content-Type": "application/json", "x-csrf-token": csrf_token },
        body: JSON.stringify({ expected_version: data.policy.version, day_offsets: days, reason }),
      });
      if (!response.ok) throw new Error();
      setData({ ...data, policy: await response.json() as Dashboard["policy"] });
      setReason(""); setMessage(t.saved);
    } catch { setPaused(true); setMessage(pausedLabel); } finally { writing.current = false; setBusy(false); }
  }
  async function refresh() {
    if (writing.current) return;
    writing.current = true; setBusy(true);
    try {
      const response = await fetch(`/api/businesses/organizations/${org}/staff`, { cache: "no-store" });
      if (!response.ok) throw new Error();
      setData(await response.json() as Dashboard); setPaused(false);
      setMessage(locale === "ta" ? "சேமித்த அட்டவணை புதுப்பிக்கப்பட்டது. உங்கள் உள்ளீட்டை ஒப்பிடவும்." :
        "Saved schedule refreshed. Compare your input before saving.");
    } catch { setMessage(t.error); } finally { writing.current = false; setBusy(false); }
  }
  return <><header className="program-heading"><div>
    <h1>{t.title}</h1><p>{t.intro}</p></div></header><p role="status">{message}</p>
    <button type="button" disabled={busy} onClick={() => void refresh()}>{refreshLabel}</button>
    {data && <><section className="program-panel"><h2>{t.policy}</h2>
      <p>{locale === "ta" ? "சேமித்த அட்டவணை" : "Saved schedule"}: {data.policy.day_offsets.join(", ")} · v{data.policy.version}</p>
      {canManage ? <fieldset disabled={busy}><label>{t.policy}<input value={offsets} onChange={(e) => setOffsets(e.target.value)}
        aria-describedby="business-schedule-help" /></label>
        <p id="business-schedule-help">{locale === "ta" ? "ஏறுவரிசையில் காற்புள்ளியால் பிரிக்கப்பட்ட நாட்கள்" : "Ascending days separated by commas"}</p>
        <label>{t.reason}<input value={reason} maxLength={500} onChange={(e) => setReason(e.target.value)} /></label>
        <button type="button" disabled={busy || paused || reason.trim().length < 3} onClick={() => void save()}>{t.save}</button></fieldset>
        : <p>{data.policy.day_offsets.join(", ")}</p>}</section>
      <section className="program-panel"><h2>{t.title}</h2>
        {data.profiles.length ? <ul className="program-list">{data.profiles.map((item) =>
          <li key={item.profile_id}><strong>{item.name}</strong> · {businessValue(locale, item.stage)}
            <p>{t.due}: {item.due_count} · {t.completed}: {item.completed_count}</p></li>)}</ul>
          : <p>{t.empty}</p>}</section></>}
  </>;
}
