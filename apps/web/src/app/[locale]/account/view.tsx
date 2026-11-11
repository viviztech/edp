"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import type { components } from "../../../lib/api-contracts";
import type { AuthMessages } from "../../../lib/auth-messages";
import { StaffModuleNav } from "../../../components/staff-module-nav";

type Mode =
  | "login"
  | "register"
  | "request-verification"
  | "verify"
  | "request-reset"
  | "reset";
type Profile = components["schemas"]["Profile"];
type Session =
  components["schemas"]["app__modules__identity__schemas__SessionView"];

const participantPermissions = new Set(["system.access", "participant.self", "lms.learn", "mentoring.view"]);
function hasStaffWorkspace(permissions: string[]) {
  return permissions.includes("system.access") &&
    (!permissions.includes("participant.self") || permissions.some((permission) => !participantPermissions.has(permission)));
}

export default function Account({
  text,
  locale,
  selfServiceEnabled = true,
}: {
  text: AuthMessages;
  locale: string;
  selfServiceEnabled?: boolean;
}) {
  const [mode, setMode] = useState<Mode>("login");
  const [profile, setProfile] = useState<Profile | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const labels = locale === "ta"
    ? { welcome: "உங்கள் பணியிடங்களைத் தேர்ந்தெடுக்கவும்", overview: "கணக்கு மற்றும் அணுகல்", program: "எனது திட்டம்", learning: "எனது கற்றல்", admin: "பணியாளர் பணியிடம்", access: "உங்கள் அணுகல்", devices: "உங்கள் சாதனங்களை நிர்வகிக்கவும்", signIn: "தொடர உங்கள் கணக்கில் உள்நுழைக", choose: "கணக்கு உதவி" }
    : { welcome: "Choose where you want to go", overview: "Account and access", program: "My program", learning: "My learning", admin: "Staff workspace", access: "Your access", devices: "Manage your signed-in devices", signIn: "Sign in to continue to your workspace", choose: "Account help" };
  const modes: [Mode, string][] = selfServiceEnabled
    ? [
        ["login", text.login],
        ["register", text.register],
        ["request-verification", text.requestVerification],
        ["verify", text.verify],
        ["request-reset", text.requestReset],
        ["reset", text.reset],
      ]
    : [["login", text.login]];
  async function load() {
    try {
      const response = await fetch("/api/session/me", { cache: "no-store" });
      if (response.status === 401) {
        setProfile(null);
        setSessions([]);
        return;
      }
      if (!response.ok) throw new Error("load");
      setProfile(await response.json());
      const devices = await fetch("/api/session/sessions", {
        cache: "no-store",
      });
      if (!devices.ok) throw new Error("load");
      setSessions(await devices.json());
    } catch {
      setMessage(text.error);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    let active = true;
    fetch("/api/session/me", { cache: "no-store" })
      .then(async (response) => {
        if (response.status === 401) return { person: null, devices: [] };
        if (!response.ok) throw new Error("load");
        const person: Profile = await response.json();
        const devicesResponse = await fetch("/api/session/sessions", {
          cache: "no-store",
        });
        if (!devicesResponse.ok) throw new Error("load");
        const devices: Session[] = await devicesResponse.json();
        return { person, devices };
      })
      .then(({ person, devices }) => {
        if (active) {
          setProfile(person);
          setSessions(devices);
        }
      })
      .catch(() => {
        if (active) setMessage(text.error);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [text.error]);
  async function mutate(path: string, data: object) {
    const csrfResponse = await fetch("/api/session/csrf", {
      cache: "no-store",
    });
    if (!csrfResponse.ok) throw new Error("service_unavailable");
    const csrf = await csrfResponse.json();
    const response = await fetch("/api/session/" + path, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrf.csrf_token,
      },
      body: JSON.stringify(data),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error?.code ?? "request_failed");
  }
  function showError(error: unknown) {
    const code = error instanceof Error ? error.message : "";
    setMessage(
      code === "invalid_credentials"
        ? text.invalid
        : code === "rate_limited"
          ? text.limited
          : code === "invalid_session"
            ? text.sessionExpired
            : code === "delivery_unavailable" || code === "service_unavailable"
              ? text.unavailable
              : text.error,
    );
  }
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const fields = new FormData(form);
    const data: Record<string, string> = {};
    for (const [key, value] of fields) data[key] = String(value);
    if (mode === "register") data.locale = locale;
    if (mode === "login") data.device_name = "Web browser";
    setBusy(true);
    setMessage("");
    try {
      await mutate(mode, data);
      form.reset();
      if (mode === "login") await load();
      else
        setMessage(
          ["register", "request-reset", "request-verification"].includes(mode)
            ? text.accepted
            : text.completed,
        );
    } catch (error) {
      showError(error);
    } finally {
      setBusy(false);
    }
  }
  async function action(path: string) {
    setBusy(true);
    setMessage("");
    try {
      await mutate(path, {});
      await load();
    } catch (error) {
      showError(error);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="account-workspace" aria-busy={loading || busy}>
      <div className="account-intro"><p className="account-eyebrow">CSJE · {labels.overview}</p>
        <h1>{text.title}</h1>
        <p>{profile ? labels.welcome : labels.signIn}</p></div>
      {message && <p className="account-message" role="status">{message}</p>}
      {loading ? (
        <p role="status">{text.loading}</p>
      ) : profile ? (
        <>
          <div className="account-profile"><span aria-hidden="true">{profile.display_name.trim().charAt(0).toUpperCase() || "•"}</span><div><small>{labels.access}</small><strong>{profile.display_name}</strong></div></div>
          <div className="account-panel"><h2>{text.organizations}</h2>
          {profile.grants.length === 0 ? (
            <p>{text.noOrganizations}</p>
          ) : (
            <ul className="account-organizations">
              {profile.grants.map((grant) => (
                <li key={grant.organization_id}>
                  <strong>{grant.organization_name}</strong>
                  <div className="account-workspace-links">
                    {grant.permissions.includes("participant.self") && <Link href={`/${locale}/participant?organization=${grant.organization_id}`}>{labels.program}</Link>}
                    {grant.permissions.includes("lms.learn") && <Link href={`/${locale}/learning?organization=${grant.organization_id}`}>{labels.learning}</Link>}
                    {hasStaffWorkspace(grant.permissions) && <Link href={`/${locale}/admin?organization=${grant.organization_id}`}>{labels.admin}</Link>}
                    {selfServiceEnabled && <Link href={`/${locale}/applications?organization=${grant.organization_id}`}>{text.application}</Link>}
                  </div>
                  {!grant.permissions.includes("system.access") && <StaffModuleNav locale={locale === "ta" ? "ta" : "en"} organization={grant.organization_id} permissions={grant.permissions} />}
                </li>
              ))}
            </ul>
          )}</div>
          <div className="account-panel"><h2>{text.sessions}</h2><p className="account-panel-help">{labels.devices}</p>
          <div className="actions account-actions">
            <button disabled={busy} onClick={() => action("logout")}>
              {text.logout}
            </button>
            <button disabled={busy} onClick={() => action("logout-all")}>
              {text.logoutAll}
            </button>
          </div>
          {sessions.length === 0 ? (
            <p>{text.noSessions}</p>
          ) : (
            <ul className="account-devices">
              {sessions.map((device) => (
                <li key={device.id}>
                  {device.device_name}{" "}
                  {device.current ? "(" + text.current + ")" : ""}{" "}
                  <button
                    disabled={busy}
                    onClick={() => action("revoke/" + device.id)}
                  >
                    {text.revoke}
                  </button>
                </li>
              ))}
            </ul>
          )}
          </div>
        </>
      ) : (
        <>
          {modes.length > 1 && <nav className="actions account-mode-nav" aria-label={labels.choose}>
            {modes.map(([key, label]) => (
              <button
                type="button"
                key={key}
                disabled={busy}
                aria-pressed={mode === key}
                onClick={() => {
                  setMode(key);
                  setMessage("");
                }}
              >
                {label}
              </button>
            ))}
          </nav>}
          <form key={mode} onSubmit={submit} className="account-form">
            {mode === "register" && (
              <label>
                {text.name}
                <input
                  name="display_name"
                  autoComplete="name"
                  required
                  maxLength={120}
                />
              </label>
            )}
            {!["verify", "reset"].includes(mode) && (
              <label>
                {text.email}
                <input
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  maxLength={254}
                />
              </label>
            )}
            {["verify", "reset"].includes(mode) && (
              <label>
                {text.token}
                <input
                  name="token"
                  autoComplete="one-time-code"
                  required
                  minLength={32}
                  maxLength={256}
                />
              </label>
            )}
            {["login", "register", "reset"].includes(mode) && (
              <div>
                <label>
                  {text.password}
                  <input
                    name="password"
                    type="password"
                    autoComplete={
                      mode === "login" ? "current-password" : "new-password"
                    }
                    required
                    minLength={12}
                    maxLength={128}
                    aria-describedby="password-help"
                  />
                </label>
                <small id="password-help">{text.passwordHelp}</small>
              </div>
            )}
            <button type="submit" disabled={busy}>
              {busy ? text.loading : modes.find(([key]) => key === mode)?.[1]}
            </button>
          </form>
        </>
      )}
    </section>
  );
}
