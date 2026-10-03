"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import type { components } from "../../../../lib/api-contracts";
import { attendanceMessages } from "../../../../lib/attendance-messages";

type Locale = "en" | "ta";
type Workspace = components["schemas"]["StaffAttendanceWorkspace"];
type WindowCreated = components["schemas"]["WindowCreatedView"];
type AttendanceStatus = "present" | "absent" | "late" | "excused";

const statuses: AttendanceStatus[] = ["present", "absent", "late", "excused"];

export default function AttendanceWorkspace({ org, locale }: { org: string; locale: Locale }) {
  const text = attendanceMessages[locale];
  const root = `/api/attendance/organizations/${org}`;
  const [workspace, setWorkspace] = useState<Workspace>({ sessions: [] });
  const [tokens, setTokens] = useState<Record<string, { token: string; qr: string }>>({});
  const [busy, setBusy] = useState(true);
  const [message, setMessage] = useState<string>(text.loading);
  const label = (en: string, ta: string) => locale === "ta" ? ta : en;

  const load = useCallback(async () => {
    const response = await fetch(root + "/staff-workspace", { cache: "no-store" });
    if (!response.ok) throw new Error("request_failed");
    setWorkspace(await response.json() as Workspace);
  }, [root]);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        await load();
        if (active) setMessage("");
      } catch {
        if (active) setMessage(text.error);
      } finally {
        if (active) setBusy(false);
      }
    })();
    return () => { active = false; };
  }, [load, text.error]);

  async function command(path: string, method: "POST" | "PUT", body: object) {
    setBusy(true);
    try {
      const csrf = await fetch("/api/session/csrf", { cache: "no-store" });
      if (!csrf.ok) throw new Error("csrf_failed");
      const response = await fetch(root + path, {
        method,
        headers: {
          "Content-Type": "application/json",
          "x-csrf-token": (await csrf.json() as { csrf_token: string }).csrf_token,
        },
        body: JSON.stringify(body),
      });
      if (!response.ok) throw new Error("request_failed");
      setMessage(text.saved);
      return response;
    } catch {
      setMessage(text.error);
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function savePolicy(event: FormEvent<HTMLFormElement>, cohortId: string, version?: number) {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    const response = await command("/policy", "PUT", {
      cohort_id: cohortId,
      expected_version: version,
      threshold_percent: Number(data.threshold_percent),
      late_after_minutes: Number(data.late_after_minutes),
      opens_before_minutes: Number(data.opens_before_minutes),
      closes_after_minutes: Number(data.closes_after_minutes),
      reason: data.reason,
    });
    if (response) await load();
  }

  async function openWindow(sessionId: string) {
    const response = await command("/windows", "POST", {
      session_id: sessionId,
      reason: "Trainer opened the scheduled check-in window",
    });
    if (!response) return;
    const created = await response.json() as WindowCreated;
    setTokens((current) => ({
      ...current,
      [sessionId]: { token: created.check_in_token, qr: created.qr_svg_data_url },
    }));
    await load();
  }

  async function closeWindow(windowId: string, version: number) {
    if (await command(`/windows/${windowId}/close`, "POST", {
      expected_version: version,
      reason: "Trainer closed the session check-in window",
    })) await load();
  }

  async function saveRecord(
    event: FormEvent<HTMLFormElement>,
    sessionId: string,
    enrollmentId: string,
    recordId?: string,
    version?: number,
  ) {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    const path = recordId ? `/records/${recordId}/correct` : `/sessions/${sessionId}/records`;
    const body = recordId
      ? { expected_version: version, status: data.status, reason: data.reason }
      : { enrollment_id: enrollmentId, status: data.status, reason: data.reason };
    if (await command(path, "POST", body)) await load();
  }

  return <section aria-busy={busy}>
    <p role="status">{busy ? text.loading : message}</p>
    {!busy && workspace.sessions.length === 0 && <p>{text.empty}</p>}
    <div className="program-grid">{workspace.sessions.map((session) => {
      const fresh = tokens[session.session_id];
      return <article className="program-panel" key={session.session_id}>
        <h2>{label(session.title_en, session.title_ta)}</h2>
        <p>{new Date(session.starts_at).toLocaleString(locale)} – {new Date(session.ends_at).toLocaleString(locale)}</p>
        <span className={`program-state program-state-${session.session_status}`}>{session.session_status}</span>
        <h3>{text.policy}</h3>
        <form onSubmit={(event) => savePolicy(event, session.cohort_id, session.policy?.version)}>
          <label>{text.threshold}<input name="threshold_percent" type="number" min="1" max="100" defaultValue={session.policy?.threshold_percent ?? 75} required /></label>
          <label>{text.lateAfter}<input name="late_after_minutes" type="number" min="0" max="240" defaultValue={session.policy?.late_after_minutes ?? 15} required /></label>
          <label>{text.opensBefore}<input name="opens_before_minutes" type="number" min="0" max="1440" defaultValue={session.policy?.opens_before_minutes ?? 15} required /></label>
          <label>{text.closesAfter}<input name="closes_after_minutes" type="number" min="0" max="1440" defaultValue={session.policy?.closes_after_minutes ?? 30} required /></label>
          <label>{text.reason}<input name="reason" minLength={3} maxLength={500} required /></label>
          <button disabled={busy} type="submit">{text.savePolicy}</button>
        </form>
        {session.policy && !session.window && <button disabled={busy} onClick={() => void openWindow(session.session_id)}>{text.openWindow}</button>}
        {session.window && <div>
          <p>{text.qrHelp}</p>
          {fresh && <><object
            width="220"
            height="220"
            aria-label={text.checkInCode}
            data={fresh.qr}
            type="image/svg+xml"
          >{text.checkInCode}</object>
          <code data-check-in-token>{fresh.token}</code></>}
          <p>{new Date(session.window.opens_at).toLocaleString(locale)} – {new Date(session.window.closes_at).toLocaleString(locale)}</p>
          <button disabled={busy} onClick={() => void closeWindow(session.window!.id, session.window!.version)}>{text.closeWindow}</button>
        </div>}
        <h3>{text.register}</h3>
        <ul className="program-list">{session.participants.map((participant) => <li key={participant.enrollment_id}>
          <strong>{participant.display_name}</strong>
          <span>{participant.record ? text[participant.record.status] : text.unmarked}</span>
          <form onSubmit={(event) => saveRecord(event, session.session_id, participant.enrollment_id, participant.record?.id, participant.record?.version)}>
            <select name="status" defaultValue={participant.record?.status ?? "present"}>
              {statuses.map((status) => <option key={status} value={status}>{text[status]}</option>)}
            </select>
            <input name="reason" aria-label={text.reason} placeholder={text.reason} minLength={3} maxLength={500} required />
            <button disabled={busy} type="submit">{participant.record ? text.correct : text.mark}</button>
          </form>
        </li>)}</ul>
      </article>;
    })}</div>
  </section>;
}
