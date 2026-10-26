import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import ParticipantTimelineView from "./view";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

const starts = "2026-10-24T08:00:00Z";
const ends = "2026-10-24T09:00:00Z";
const states = ["submitted", "selected", "active", "withdrawn", "completed", "cancelled", "scheduled"];

function timeline() {
  return {
    sessions: [{ id: "session", title_en: "Business workshop", title_ta: "தொழில் பயிலரங்கம்", starts_at: starts, ends_at: ends, status: "scheduled" }],
    events: states.map((state, index) => ({ resource_id: String(index), kind: "enrollment", state, occurred_at: starts, title_en: `Event ${index}`, title_ta: `நிகழ்வு ${index}` })),
  };
}

describe("participant schedule localization", () => {
  it.each([
    { locale: "en" as const, title: "Business workshop", sessions: "Sessions", timeline: "Timeline", startLabel: "Starts:", endLabel: "Ends:", dateLabel: "Date:", statuses: ["Submitted", "Selected", "Active", "Withdrawn", "Completed", "Cancelled", "Scheduled"] },
    { locale: "ta" as const, title: "தொழில் பயிலரங்கம்", sessions: "அமர்வுகள்", timeline: "காலவரிசை", startLabel: "தொடக்கம்:", endLabel: "முடிவு:", dateLabel: "தேதி:", statuses: ["சமர்ப்பிக்கப்பட்டது", "தேர்ந்தெடுக்கப்பட்டது", "செயலில் உள்ளது", "விலகப்பட்டது", "நிறைவடைந்தது", "ரத்து செய்யப்பட்டது", "திட்டமிடப்பட்டது"] },
  ])("renders translated state and date labels for $locale", async ({ locale, title, sessions, timeline: timelineLabel, startLabel, endLabel, dateLabel, statuses }) => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(timeline()), { status: 200 })));
    render(<ParticipantTimelineView org="organization" locale={locale} />);
    await screen.findByText(title);
    const sessionPanel = screen.getByRole("heading", { name: sessions }).closest("section")!;
    const eventPanel = screen.getByRole("heading", { name: timelineLabel }).closest("section")!;
    for (const status of statuses) expect(within(eventPanel).getByText(status)).toBeTruthy();
    expect(within(sessionPanel).getByText(statuses[6])).toBeTruthy();
    expect(within(sessionPanel).getByText(new RegExp(startLabel))).toBeTruthy();
    expect(within(sessionPanel).getByText(new RegExp(endLabel))).toBeTruthy();
    expect(within(eventPanel).getAllByText(new RegExp(dateLabel))).toHaveLength(states.length);
    const date = sessionPanel.querySelector("time");
    expect(date?.getAttribute("datetime")).toBe(starts);
    expect(date?.textContent).toBe(new Intl.DateTimeFormat(locale === "ta" ? "ta-IN" : "en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(starts)));
    expect(sessionPanel.querySelectorAll("time")[1].getAttribute("datetime")).toBe(ends);
  });

  it("uses a localized fallback for an unfamiliar state", async () => {
    const data = timeline();
    data.events = [{ ...data.events[0], state: "future_internal_state" }];
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(data), { status: 200 })));
    render(<ParticipantTimelineView org="organization" locale="ta" />);
    expect(await screen.findByText("நிலை கிடைக்கவில்லை")).toBeTruthy();
    expect(screen.queryByText("future_internal_state")).toBeNull();
  });
});
