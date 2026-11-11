"use client";
import { Card } from "../../../components/ui/card";
import { Input } from "../../../components/ui/input";
import { Button } from "../../../components/ui/button";


import { FormEvent, useCallback, useEffect, useState } from "react";
import type { components } from "../../../lib/api-contracts";
import { attendanceMessages } from "../../../lib/attendance-messages";

type Locale = "en" | "ta";
type Attendance = components["schemas"]["MyAttendanceView"];

export default function LearnerAttendance({ org, locale, initialToken }: { org: string; locale: Locale; initialToken: string }) {
  const text = attendanceMessages[locale];
  const root = `/api/attendance/organizations/${org}`;
  const [attendance, setAttendance] = useState<Attendance>({ enrollments: [] });
  const [busy, setBusy] = useState(true);
  const [message, setMessage] = useState<string>(text.loading);
  const label = (en: string, ta: string) => locale === "ta" ? ta : en;

  const load = useCallback(async () => {
    const response = await fetch(root + "/my-attendance", { cache: "no-store" });
    if (!response.ok) throw new Error("request_failed");
    setAttendance(await response.json() as Attendance);
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

  async function checkIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    try {
      const data = new FormData(event.currentTarget);
      const raw = String(data.get("token") ?? "").trim().replace(/^edp-attendance:/, "");
      const csrf = await fetch("/api/session/csrf", { cache: "no-store" });
      if (!csrf.ok) throw new Error("csrf_failed");
      const response = await fetch(root + "/check-in", {
        method: "POST",
        headers: { "Content-Type": "application/json", "x-csrf-token": (await csrf.json() as { csrf_token: string }).csrf_token },
        body: JSON.stringify({ token: raw }),
      });
      if (!response.ok) throw new Error("request_failed");
      await load();
      setMessage(text.saved);
    } catch {
      setMessage(text.error);
    } finally {
      setBusy(false);
    }
  }

  return <>
    <header className="program-heading"><div><p className="eyebrow">{text.eyebrow}</p>
      <h1>{text.learnerTitle}</h1><p>{text.learnerIntro}</p></div></header>
    <form className="participant-check-in program-panel" onSubmit={checkIn}>
      <label>{text.checkInCode}<Input name="token" defaultValue={initialToken} minLength={32} maxLength={160} required /></label>
      <Button disabled={busy} type="submit">{text.checkIn}</Button>
    </form>
    <p role="status">{busy ? text.loading : message}</p>
    {!busy && !message && attendance.enrollments.length === 0 && <p className="participant-empty">{locale === "ta" ? "வருகைப் பதிவுகள் இன்னும் இல்லை." : "Your attendance records will appear here."}</p>}
    <div className="program-grid">{attendance.enrollments.map((enrollment) => <Card className="program-panel" key={enrollment.enrollment_id}>
      <h2>{label(enrollment.cohort_name_en, enrollment.cohort_name_ta)}</h2>
      <p><strong>{enrollment.summary.percent}%</strong> — {enrollment.summary.attended} {text.attended} / {enrollment.summary.required} {text.required}</p>
      <p role={enrollment.summary.low_attendance ? "alert" : undefined}>{enrollment.summary.low_attendance ? text.lowAttendance : text.onTrack}</p>
      <ul className="program-list">{enrollment.sessions.map((session) => <li key={session.session_id}>
        <strong>{label(session.title_en, session.title_ta)}</strong>
        <small>{new Date(session.starts_at).toLocaleString(locale)}</small>
        <span>{session.record ? text[session.record.status] : text.unmarked}</span>
      </li>)}</ul>
    </Card>)}</div>
  </>;
}
