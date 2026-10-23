import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { ParticipantModuleNav } from "./participant-module-nav";

const organization = "11111111-1111-4111-8111-111111111111";
afterEach(cleanup);

describe("participant navigation", () => {
  it("provides learning and all supported participant destinations in the same organization and locale", () => {
    render(<ParticipantModuleNav locale="en" organization={organization} permissions={["participant.self", "lms.learn"]} active="learning" />);
    for (const route of ["participant", "learning", "attendance", "mentoring", "business-plan", "businesses", "knowledge", "helpdesk", "impact"]) {
      expect(screen.getAllByRole("link").some(link => link.getAttribute("href") === `/en/${route}?organization=${organization}`)).toBe(true);
    }
    expect(screen.getByRole("link", { name: "My learning" }).getAttribute("aria-current")).toBe("page");
    expect(screen.getByRole("link", { name: "My account" }).getAttribute("href")).toBe("/en/account");
  });

  it("uses each actual scoped capability rather than assuming learning or participant enrollment", () => {
    const view = render(<ParticipantModuleNav locale="en" organization={organization} permissions={["participant.self"]} />);
    expect(screen.queryByRole("link", { name: "My learning" })).toBeNull();
    view.rerender(<ParticipantModuleNav locale="en" organization={organization} permissions={["lms.learn"]} />);
    expect(screen.queryByRole("link", { name: "My schedule" })).toBeNull();
    expect(screen.getAllByRole("link")).toHaveLength(2);
    view.rerender(<ParticipantModuleNav locale="en" organization={organization} permissions={["system.access", "lms.course.view"]} />);
    expect(screen.queryByRole("navigation")).toBeNull();
  });

  it("renders readable Tamil navigation including helpdesk and business outcomes", () => {
    render(<ParticipantModuleNav locale="ta" organization={organization} permissions={["participant.self", "lms.learn"]} active="impact" />);
    expect(screen.getByRole("navigation", { name: "பங்கேற்பாளர் வழிசெலுத்தல்" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "உதவி மையம்" }).getAttribute("href")).toBe(`/ta/helpdesk?organization=${organization}`);
    expect(screen.getByRole("link", { name: "எனது தொழில் விளைவுகள்" }).getAttribute("aria-current")).toBe("page");
    expect(screen.getByRole("navigation").textContent).not.toMatch(/\?{2,}|à®|Ã/);
  });
});
