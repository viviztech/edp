"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import type { components } from "../../../../lib/api-contracts";
import { attendanceMessages } from "../../../../lib/attendance-messages";
import { Button } from "../../../../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../../../components/ui/card";
import { Input } from "../../../../components/ui/input";
import { CalendarDays, ClipboardList, QrCode, Settings2 } from "lucide-react";

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
  const sessionStates = locale === "ta"
    ? { scheduled: "திட்டமிடப்பட்டது", completed: "நிறைவடைந்தது", cancelled: "ரத்து செய்யப்பட்டது" }
    : { scheduled: "Scheduled", completed: "Completed", cancelled: "Cancelled" };

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

  return <section className="attendance-workspace" aria-busy={busy}>
    {(busy || message) && <p className="attendance-feedback" role="status">{busy ? text.loading : message}</p>}
    {!busy && !message && workspace.sessions.length === 0 && <Card className="attendance-empty"><CardContent><CalendarDays aria-hidden="true" /><p>{text.empty}</p></CardContent></Card>}
    <div className="attendance-session-list">{workspace.sessions.map((session) => {
      const fresh = tokens[session.session_id];
      return <Card className="attendance-session" key={session.session_id} role="article" aria-label={label(session.title_en, session.title_ta)}>
        <CardHeader className="attendance-session-heading"><div><CardTitle role="heading" aria-level={2}>{label(session.title_en, session.title_ta)}</CardTitle>
        <CardDescription>{new Date(session.starts_at).toLocaleString(locale)} – {new Date(session.ends_at).toLocaleString(locale)}</CardDescription></div>
        <span className={`program-state program-state-${session.session_status}`}>{sessionStates[session.session_status]}</span></CardHeader>
        <CardContent className="attendance-session-content">
        <details className="attendance-policy"><summary><Settings2 size={17} aria-hidden="true" />{text.policy}</summary>
        <form className="attendance-policy-form" onSubmit={(event) => savePolicy(event, session.cohort_id, session.policy?.version)}>
          <label>{text.threshold}<Input name="threshold_percent" type="number" min="1" max="100" defaultValue={session.policy?.threshold_percent ?? 75} required /></label>
          <label>{text.lateAfter}<Input name="late_after_minutes" type="number" min="0" max="240" defaultValue={session.policy?.late_after_minutes ?? 15} required /></label>
          <label>{text.opensBefore}<Input name="opens_before_minutes" type="number" min="0" max="1440" defaultValue={session.policy?.opens_before_minutes ?? 15} required /></label>
          <label>{text.closesAfter}<Input name="closes_after_minutes" type="number" min="0" max="1440" defaultValue={session.policy?.closes_after_minutes ?? 30} required /></label>
          <label className="attendance-reason">{text.reason}<Input name="reason" minLength={3} maxLength={500} required /></label>
          <Button disabled={busy} type="submit">{text.savePolicy}</Button>
        </form></details>
        {session.policy && !session.window && <div className="attendance-window-actions"><Button type="button" disabled={busy} onClick={() => void openWindow(session.session_id)}><QrCode aria-hidden="true" />{text.openWindow}</Button></div>}
        {session.window && <div className="attendance-window">
          <p>{fresh ? text.qrHelp : locale === "ta" ? "QR குறியீடு சாளரத்தைத் திறந்த உடன் மட்டுமே காண்பிக்கப்படும்." : "The QR code is shown only when the check-in window is opened."}</p>
          {fresh && <><object
            width="220"
            height="220"
            aria-label={text.checkInCode}
            data={fresh.qr}
            type="image/svg+xml"
          >{text.checkInCode}</object>
          <code data-check-in-token>{fresh.token}</code></>}
          <p>{new Date(session.window.opens_at).toLocaleString(locale)} – {new Date(session.window.closes_at).toLocaleString(locale)}</p>
          <Button type="button" variant="outline" disabled={busy} onClick={() => void closeWindow(session.window!.id, session.window!.version)}>{text.closeWindow}</Button>
        </div>}
        <div className="attendance-register-heading"><ClipboardList size={18} aria-hidden="true" /><h3>{text.register}</h3></div>
        {session.participants.length === 0 && <p className="attendance-register-empty">{locale === "ta" ? "இந்த அமர்வில் பங்கேற்பாளர்கள் இல்லை." : "There are no participants in this session."}</p>}
        <ul className="program-list">{session.participants.map((participant) => <li key={participant.enrollment_id}>
          <div className="attendance-person"><strong>{participant.display_name}</strong>
          <span className="attendance-person-state">{participant.record ? text[participant.record.status] : text.unmarked}</span></div>
          <form className="attendance-record-form" onSubmit={(event) => saveRecord(event, session.session_id, participant.enrollment_id, participant.record?.id, participant.record?.version)}>
            <label><span className="attendance-visually-hidden">{text.register}: {participant.display_name}</span><select name="status" defaultValue={participant.record?.status ?? "present"}>
              {statuses.map((status) => <option key={status} value={status}>{text[status]}</option>)}
            </select></label>
            <Input name="reason" aria-label={text.reason} placeholder={text.reason} minLength={3} maxLength={500} required />
            <Button disabled={busy} type="submit">{participant.record ? text.correct : text.mark}</Button>
          </form>
        </li>)}</ul>
        </CardContent></Card>;
    })}</div>
  </section>;
}
