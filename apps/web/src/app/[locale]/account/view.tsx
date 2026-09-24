"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import type { components } from "../../../lib/api-contracts";
import type { AuthMessages } from "../../../lib/auth-messages";

type Mode = "login" | "register" | "request-verification" | "verify" | "request-reset" | "reset";
type Profile = components["schemas"]["Profile"];
type Session = components["schemas"]["app__modules__identity__schemas__SessionView"];

export default function Account({ text, locale }: { text: AuthMessages; locale: string }) {
  const [mode, setMode] = useState<Mode>("login");
  const [profile, setProfile] = useState<Profile | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const modes: [Mode, string][] = [["login", text.login], ["register", text.register], ["request-verification", text.requestVerification], ["verify", text.verify], ["request-reset", text.requestReset], ["reset", text.reset]];
  async function load() {
    try {
      const response = await fetch("/api/session/me", { cache: "no-store" });
      if (response.status === 401) { setProfile(null); setSessions([]); return; }
      if (!response.ok) throw new Error("load");
      setProfile(await response.json());
      const devices = await fetch("/api/session/sessions", { cache: "no-store" });
      if (!devices.ok) throw new Error("load");
      setSessions(await devices.json());
    } catch { setMessage(text.error); } finally { setLoading(false); }
  }
  useEffect(() => {
    let active = true;
    fetch("/api/session/me", { cache: "no-store" }).then(async response => {
      if (response.status === 401) return { person: null, devices: [] };
      if (!response.ok) throw new Error("load");
      const person: Profile = await response.json();
      const devicesResponse = await fetch("/api/session/sessions", { cache: "no-store" });
      if (!devicesResponse.ok) throw new Error("load");
      const devices: Session[] = await devicesResponse.json();
      return { person, devices };
    }).then(({ person, devices }) => {
      if (active) { setProfile(person); setSessions(devices); }
    }).catch(() => { if (active) setMessage(text.error); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [text.error]);
  async function mutate(path: string, data: object) {
    const csrfResponse = await fetch("/api/session/csrf", { cache: "no-store" });
    if (!csrfResponse.ok) throw new Error("service_unavailable");
    const csrf = await csrfResponse.json();
    const response = await fetch("/api/session/" + path, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf.csrf_token }, body: JSON.stringify(data) });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error?.code ?? "request_failed");
  }
  function showError(error: unknown) {
    const code = error instanceof Error ? error.message : "";
    setMessage(code === "invalid_credentials" ? text.invalid : code === "rate_limited" ? text.limited : code === "invalid_session" ? text.sessionExpired : code === "delivery_unavailable" || code === "service_unavailable" ? text.unavailable : text.error);
  }
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const fields = new FormData(form);
    const data: Record<string, string> = {};
    for (const [key, value] of fields) data[key] = String(value);
    if (mode === "register") data.locale = locale;
    if (mode === "login") data.device_name = "Web browser";
    setBusy(true); setMessage("");
    try {
      await mutate(mode, data); form.reset();
      if (mode === "login") await load();
      else setMessage(["register", "request-reset", "request-verification"].includes(mode) ? text.accepted : text.completed);
    } catch (error) { showError(error); } finally { setBusy(false); }
  }
  async function action(path: string) {
    setBusy(true); setMessage("");
    try { await mutate(path, {}); await load(); } catch (error) { showError(error); } finally { setBusy(false); }
  }
  return <section aria-busy={loading || busy}>
    <h1>{text.title}</h1>
    {message && <p role="status">{message}</p>}
    {loading ? <p role="status">{text.loading}</p> : profile ? <>
      <p>{profile.display_name}</p>
      <div className="actions"><button disabled={busy} onClick={() => action("logout")}>{text.logout}</button><button disabled={busy} onClick={() => action("logout-all")}>{text.logoutAll}</button></div>
      <h2>{text.sessions}</h2>
      {sessions.length === 0 ? <p>{text.noSessions}</p> : <ul>{sessions.map(device => <li key={device.id}>{device.device_name} {device.current ? "(" + text.current + ")" : ""} <button disabled={busy} onClick={() => action("revoke/" + device.id)}>{text.revoke}</button></li>)}</ul>}
      <h2>{text.organizations}</h2>
      {profile.grants.filter(grant => grant.permissions.includes("system.access")).length === 0 ? <p>{text.noOrganizations}</p> : <ul>{profile.grants.filter(grant => grant.permissions.includes("system.access")).map(grant => <li key={grant.organization_id}><Link href={"/" + locale + "/admin?organization=" + grant.organization_id}>{grant.organization_name}</Link>{" ? "}<Link href={"/" + locale + "/applications?organization=" + grant.organization_id}>{text.application}</Link></li>)}</ul>}
    </> : <>
      <nav className="actions" aria-label={text.title}>{modes.map(([key, label]) => <button type="button" key={key} disabled={busy} aria-pressed={mode === key} onClick={() => { setMode(key); setMessage(""); }}>{label}</button>)}</nav>
      <form key={mode} onSubmit={submit} className="account-form">
        {mode === "register" && <label>{text.name}<input name="display_name" autoComplete="name" required maxLength={120} /></label>}
        {!["verify", "reset"].includes(mode) && <label>{text.email}<input name="email" type="email" autoComplete="email" required maxLength={254} /></label>}
        {["verify", "reset"].includes(mode) && <label>{text.token}<input name="token" autoComplete="one-time-code" required minLength={32} maxLength={256} /></label>}
        {["login", "register", "reset"].includes(mode) && <div><label>{text.password}<input name="password" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} required minLength={12} maxLength={128} aria-describedby="password-help" /></label><small id="password-help">{text.passwordHelp}</small></div>}
        <button type="submit" disabled={busy}>{busy ? text.loading : modes.find(([key]) => key === mode)?.[1]}</button>
      </form>
    </>}
  </section>;
}
