"use client";

import { useEffect, useState } from "react";
import type { components } from "../../../lib/api-contracts";

type Timeline = components["schemas"]["ParticipantTimeline"];
type Locale = "en" | "ta";

const copy = {
  en: {
    eyebrow: "Participant portal", title: "My program schedule",
    intro: "Your enrollment journey and scheduled program sessions.",
    loading: "Loading your schedule...", error: "Your schedule could not be loaded.",
    empty: "No sessions are scheduled yet.", timeline: "Timeline", sessions: "Sessions",
    starts: "Starts", ends: "Ends", occurred: "Date", unknown: "Status unavailable",
    states: {
      scheduled: "Scheduled", completed: "Completed", cancelled: "Cancelled",
      submitted: "Submitted", selected: "Selected", active: "Active", withdrawn: "Withdrawn",
    },
  },
  ta: {
    eyebrow: "பங்கேற்பாளர் தளம்", title: "எனது திட்ட அட்டவணை",
    intro: "உங்கள் சேர்க்கைப் பயணம் மற்றும் திட்ட அமர்வுகள்.",
    loading: "அட்டவணை ஏற்றப்படுகிறது...", error: "அட்டவணையை ஏற்ற முடியவில்லை.",
    empty: "அமர்வுகள் இன்னும் திட்டமிடப்படவில்லை.", timeline: "காலவரிசை", sessions: "அமர்வுகள்",
    starts: "தொடக்கம்", ends: "முடிவு", occurred: "தேதி", unknown: "நிலை கிடைக்கவில்லை",
    states: {
      scheduled: "திட்டமிடப்பட்டது", completed: "நிறைவடைந்தது", cancelled: "ரத்து செய்யப்பட்டது",
      submitted: "சமர்ப்பிக்கப்பட்டது", selected: "தேர்ந்தெடுக்கப்பட்டது", active: "செயலில் உள்ளது", withdrawn: "விலகப்பட்டது",
    },
  },
} as const;

export default function ParticipantTimelineView({ org, locale }: { org: string; locale: Locale }) {
  const text = copy[locale];
  const [timeline, setTimeline] = useState<Timeline | null>(null);
  const [message, setMessage] = useState<string>(text.loading);

  useEffect(() => {
    let active = true;
    fetch(`/api/programs/organizations/${org}/my-timeline`, { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        return response.json() as Promise<Timeline>;
      })
      .then((body) => { if (active) { setTimeline(body); setMessage(""); } })
      .catch(() => { if (active) setMessage(text.error); });
    return () => { active = false; };
  }, [org, text.error]);

  const label = (item: { title_en: string; title_ta: string }) => locale === "ta" ? item.title_ta : item.title_en;
  const state = (value: string) => Object.hasOwn(text.states, value)
    ? text.states[value as keyof typeof text.states] : text.unknown;
  const dates = new Intl.DateTimeFormat(locale === "ta" ? "ta-IN" : "en-IN", {
    dateStyle: "medium", timeStyle: "short",
  });
  const date = (value: string) => <time dateTime={value}>{dates.format(new Date(value))}</time>;

  return <>
    <header className="program-heading"><div><p className="eyebrow">{text.eyebrow}</p>
      <h1>{text.title}</h1><p>{text.intro}</p></div></header>
    <p role="status">{message}</p>
    {timeline && <div className="program-grid">
      <section className="program-panel"><h2>{text.sessions}</h2>
        {timeline.sessions.length ? <ul className="program-list">{timeline.sessions.map((item) => <li key={item.id}>
          <strong>{label(item)}</strong>
          <small>{text.starts}: {date(item.starts_at)} · {text.ends}: {date(item.ends_at)}</small>
          <span className={`program-state program-state-${item.status}`}>{state(item.status)}</span>
        </li>)}</ul> : <p>{text.empty}</p>}
      </section>
      <section className="program-panel"><h2>{text.timeline}</h2>
        <ol className="program-list">{timeline.events.map((item) => <li key={`${item.kind}-${item.resource_id}`}>
          <strong>{label(item)}</strong><small>{text.occurred}: {date(item.occurred_at)}</small>
          <span className={`program-state program-state-${item.state}`}>{state(item.state)}</span>
        </li>)}</ol>
      </section>
    </div>}
  </>;
}
