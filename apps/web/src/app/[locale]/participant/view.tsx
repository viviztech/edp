"use client";
import { Card } from "../../../components/ui/card";

import { useEffect, useState } from "react";
import type { components } from "../../../lib/api-contracts";
type Timeline = components["schemas"]["ParticipantTimeline"]; type Locale = "en" | "ta";
const copy = {
  en: { eyebrow: "Participant portal", title: "My program schedule", intro: "Your enrollment journey and scheduled program sessions.", loading: "Loading your schedule...", error: "Your schedule could not be loaded.", noParticipant: "We couldn't find a participant record for this organization. If you expect to be enrolled, contact the program team.", empty: "No sessions are scheduled yet.", timeline: "Timeline", sessions: "Sessions", emptyTimeline: "Your program activity will appear here." },
  ta: { eyebrow: "\u0baa\u0b99\u0bcd\u0b95\u0bc7\u0bb1\u0bcd\u0baa\u0bbe\u0bb3\u0bb0\u0bcd \u0ba4\u0bb3\u0bae\u0bcd", title: "\u0b8e\u0ba9\u0ba4\u0bc1 \u0ba4\u0bbf\u0b9f\u0bcd\u0b9f \u0b85\u0b9f\u0bcd\u0b9f\u0bb5\u0ba3\u0bc8", intro: "\u0b89\u0b99\u0bcd\u0b95\u0bb3\u0bcd \u0b9a\u0bc7\u0bb0\u0bcd\u0b95\u0bcd\u0b95\u0bc8 \u0baa\u0baf\u0ba3\u0bae\u0bcd \u0bae\u0bb1\u0bcd\u0bb1\u0bc1\u0bae\u0bcd \u0ba4\u0bbf\u0b9f\u0bcd\u0b9f \u0b85\u0bae\u0bb0\u0bcd\u0bb5\u0bc1\u0b95\u0bb3\u0bcd.", loading: "\u0b85\u0b9f\u0bcd\u0b9f\u0bb5\u0ba3\u0bc8 \u0b8f\u0bb1\u0bcd\u0bb1\u0baa\u0bcd\u0baa\u0b9f\u0bc1\u0b95\u0bbf\u0bb1\u0ba4\u0bc1...", error: "\u0b85\u0b9f\u0bcd\u0b9f\u0bb5\u0ba3\u0bc8\u0baf\u0bc8 \u0b8f\u0bb1\u0bcd\u0bb1 \u0bae\u0bc1\u0b9f\u0bbf\u0baf\u0bb5\u0bbf\u0bb2\u0bcd\u0bb2\u0bc8.", empty: "\u0b85\u0bae\u0bb0\u0bcd\u0bb5\u0bc1\u0b95\u0bb3\u0bcd \u0b87\u0ba9\u0bcd\u0ba9\u0bc1\u0bae\u0bcd \u0ba4\u0bbf\u0b9f\u0bcd\u0b9f\u0bae\u0bbf\u0b9f\u0baa\u0bcd\u0baa\u0b9f\u0bb5\u0bbf\u0bb2\u0bcd\u0bb2\u0bc8.", timeline: "\u0b95\u0bbe\u0bb2\u0bb5\u0bb0\u0bbf\u0b9a\u0bc8", emptyTimeline: "\u0b89\u0b99\u0bcd\u0b95\u0bb3\u0bcd \u0ba4\u0bbf\u0b9f\u0bcd\u0b9f\u0b9a\u0bcd \u0b9a\u0bc6\u0baf\u0bb2\u0bcd\u0baa\u0bbe\u0b9f\u0bc1\u0b95\u0bb3\u0bcd \u0b87\u0b99\u0bcd\u0b95\u0bc1 \u0ba4\u0bcb\u0ba9\u0bcd\u0bb1\u0bc1\u0bae\u0bcd.", sessions: "\u0b85\u0bae\u0bb0\u0bcd\u0bb5\u0bc1\u0b95\u0bb3\u0bcd" },
} as const;
export default function ParticipantTimelineView({ org, locale }: { org: string; locale: Locale }) {
  const text = copy[locale];
  const [result, setResult] = useState<{ org: string; locale: Locale; timeline: Timeline | null; message: string }>({ org, locale, timeline: null, message: text.loading });
  const current = result.org === org && result.locale === locale ? result : { timeline: null, message: text.loading };
  const { timeline, message } = current;
  useEffect(() => {
    let active = true;
    fetch(`/api/programs/organizations/${org}/my-timeline`, { cache: "no-store" }).then(async (response) => {
      // The BFF also uses 404 for invalid paths, so only interpret a valid organization URL.
      if (response.status === 404 && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(org)) {
        const body = await response.json() as { error?: { code?: string } };
        if (body.error?.code === "not_found") {
          if (active) setResult({ org, locale, timeline: null, message: locale === "ta" ? "இந்த அமைப்பிற்கான பங்கேற்பாளர் பதிவைக் கண்டறிய முடியவில்லை. நீங்கள் சேர்க்கப்பட்டிருக்க வேண்டும் என எதிர்பார்த்தால், திட்டக் குழுவைத் தொடர்புகொள்ளுங்கள்." : copy.en.noParticipant });
          return;
        }
      }
      if (!response.ok) throw new Error();
      const body = await response.json() as Timeline;
      if (active) setResult({ org, locale, timeline: body, message: "" });
    }).catch(() => { if (active) setResult({ org, locale, timeline: null, message: text.error }); });
    return () => { active = false; };
  }, [org, locale, text.error, text.loading]);
  const label = (item: { title_en: string; title_ta: string }) => locale === "ta" ? item.title_ta : item.title_en;
  return <><header className="program-heading"><div><p className="eyebrow">{text.eyebrow}</p><h1>{text.title}</h1><p>{text.intro}</p></div></header><p role="status">{message}</p>{timeline && <div className="program-grid"><Card className="program-panel"><h2>{text.sessions}</h2>{timeline.sessions.length ? <ul className="program-list">{timeline.sessions.map((item) => <li key={item.id}><strong>{label(item)}</strong><small>{new Date(item.starts_at).toLocaleString(locale)} {"\u2013"} {new Date(item.ends_at).toLocaleString(locale)}</small><span className={`program-state program-state-${item.status}`}>{item.status}</span></li>)}</ul> : <p>{text.empty}</p>}</Card><Card className="program-panel"><h2>{text.timeline}</h2>{timeline.events.length ? <ol className="program-list">{timeline.events.map((item) => <li key={`${item.kind}-${item.resource_id}`}><strong>{label(item)}</strong><small>{new Date(item.occurred_at).toLocaleString(locale)}</small><span className={`program-state program-state-${item.state}`}>{item.state}</span></li>)}</ol> : <p>{text.emptyTimeline}</p>}</Card></div>}</>;
}
