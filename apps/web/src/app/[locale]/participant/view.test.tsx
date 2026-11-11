import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ParticipantTimelineView from "./view";

const org = "11111111-1111-4111-8111-111111111111";
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("participant timeline", () => {
  it("explains a missing participant record and suggests contacting the program team", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ status: 404, ok: false, json: async () => ({ error: { code: "not_found" } }) }));
    render(<ParticipantTimelineView org={org} locale="en" />);
    expect(await screen.findByText(/couldn't find a participant record/i)).toBeTruthy();
    expect(screen.getByText(/contact the program team/i)).toBeTruthy();
  });

  it("shows the missing-record guidance in Tamil", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ status: 404, ok: false, json: async () => ({ error: { code: "not_found" } }) }));
    render(<ParticipantTimelineView org={org} locale="ta" />);
    expect(await screen.findByText(/பங்கேற்பாளர் பதிவைக் கண்டறிய முடியவில்லை/)).toBeTruthy();
  });

  it.each([403, 500])("keeps the generic error for status %i", async (status) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ status, ok: false }));
    render(<ParticipantTimelineView org={org} locale="en" />);
    expect(await screen.findByText("Your schedule could not be loaded.")).toBeTruthy();
    expect(screen.queryByText(/couldn't find a participant record/i)).toBeNull();
  });

  it("keeps the generic error for a 404 from a malformed organization path", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ status: 404, ok: false, json: async () => ({ error: { code: "not_found" } }) }));
    render(<ParticipantTimelineView org="invalid" locale="en" />);
    expect(await screen.findByText("Your schedule could not be loaded.")).toBeTruthy();
  });

  it("does not interpret an unknown 404 error as a missing participant", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ status: 404, ok: false, json: async () => ({ error: { code: "unknown" } }) }));
    render(<ParticipantTimelineView org={org} locale="en" />);
    expect(await screen.findByText("Your schedule could not be loaded.")).toBeTruthy();
  });
});
