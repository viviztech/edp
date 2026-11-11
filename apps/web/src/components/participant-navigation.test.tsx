import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { ParticipantNavigation } from "./participant-navigation";

afterEach(() => { cleanup(); delete process.env.PUBLIC_SELF_SERVICE_ENABLED; });

describe("participant navigation", () => {
  it("shows only applicable workspaces and preserves the selected organization", () => {
    render(<ParticipantNavigation locale="en" organization="org-123" permissions={["participant.self"]} active="attendance" />);
    expect(screen.getByRole("link", { name: "Attendance" }).getAttribute("href")).toBe("/en/attendance?organization=org-123");
    expect(screen.getByRole("link", { name: "Attendance" }).getAttribute("aria-current")).toBe("page");
    expect(screen.queryByRole("link", { name: "Learning" })).toBeNull();
    expect(screen.getByRole("link", { name: "My business" })).toBeTruthy();
  });

  it("offers an applicant the application and account without participant-only workspaces", () => {
    process.env.PUBLIC_SELF_SERVICE_ENABLED = "true";
    render(<ParticipantNavigation locale="en" organization="org-123" permissions={[]} active="applications" />);
    expect(screen.getByRole("link", { name: "Application" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "My account" })).toBeTruthy();
    expect(screen.queryByRole("link", { name: "My program" })).toBeNull();
  });

  it("does not expose applications when public self-service is closed", () => {
    render(<ParticipantNavigation locale="en" organization="org-123" permissions={["participant.self"]} active="participant" />);
    expect(screen.queryByRole("link", { name: "Application" })).toBeNull();
  });

  it("renders Tamil labels and learning for a learning grant", () => {
    render(<ParticipantNavigation locale="ta" organization="org-123" permissions={["lms.learn"]} active="learning" />);
    expect(screen.getByRole("link", { name: "கற்றல்" }).getAttribute("href")).toBe("/ta/learning?organization=org-123");
  });
});
