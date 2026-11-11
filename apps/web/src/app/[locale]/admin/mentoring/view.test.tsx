import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import MentoringWorkspace from "./view";

const workspace = {
  mentor_candidates: [{ user_id: "mentor-1", display_name: "Test mentor", has_profile: false }],
  enrollment_candidates: [], profiles: [], expertise: [], availability: [], assignments: [],
  sessions: [], notes: [], goals: [], action_items: [], follow_ups: [], feedback_count: 0, average_rating: null,
};
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("mentoring workspace", () => {
  it("submits a mentor profile with the scoped endpoint and CSRF token", async () => {
    const request = vi.fn(async (url: string, init?: RequestInit) => ({
      ok: true,
      json: async () => url === "/api/session/csrf" ? { csrf_token: "test-token" } : init?.method === "POST" ? {} : workspace,
    }));
    vi.stubGlobal("fetch", request);
    render(<MentoringWorkspace org="org-1" locale="en" canAdmin />);
    const heading = await screen.findByRole("heading", { name: "Create mentor profile" });
    const card = heading.closest('[data-slot="card"]');
    expect(card).not.toBeNull();
    const scope = within(card as HTMLElement);
    await waitFor(() => expect(scope.getByRole("option", { name: "Test mentor" })).toBeTruthy());
    fireEvent.change(scope.getByLabelText("Mentor"), { target: { value: "mentor-1" } });
    fireEvent.change(scope.getByLabelText("Headline"), { target: { value: "Business mentor" } });
    fireEvent.submit(scope.getByRole("button", { name: "Save" }).closest("form") as HTMLFormElement);
    await waitFor(() => expect(request).toHaveBeenCalledWith("/api/mentoring/organizations/org-1/profiles", expect.objectContaining({ method: "POST", headers: expect.objectContaining({ "x-csrf-token": "test-token" }), body: JSON.stringify({ user_id: "mentor-1", headline: "Business mentor", biography: null }) })));
  });

  it("hides administration setup for non-admin mentors and shows Tamil labels", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, json: async () => workspace })));
    render(<MentoringWorkspace org="org-1" locale="ta" canAdmin={false} />);
    await screen.findByText("அமர்வுகள் மற்றும் செயல்கள்", { selector: "h2" });
    expect(screen.queryByText("வழிகாட்டி அமைப்பு")).toBeNull();
    expect(screen.getAllByLabelText("பங்கேற்பாளர்").length).toBeGreaterThan(0);
  });
});
