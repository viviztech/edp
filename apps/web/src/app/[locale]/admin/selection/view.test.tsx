import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import SelectionWorkspace from "./view";
import { selectionMessages } from "../../../../lib/selection-messages";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

function mockWorkspace() {
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: true,
    json: async () => ({ cycles: [], rubrics: [], applications: [], reviewers: [], assignments: [], aggregates: [], interviews: [], decisions: [] }),
  })));
}

describe("selection workspace navigation", () => {
  it("shows only sections available to a reviewer and links to their actual panels", async () => {
    mockWorkspace();
    render(<SelectionWorkspace org="org" actor="reviewer" locale="en" permissions={["selection.cycle.view", "selection.review"]} />);
    await screen.findByRole("heading", { name: selectionMessages.en.inbox });
    const nav = within(screen.getByRole("navigation", { name: "On this page" }));
    expect(nav.getByRole("link", { name: selectionMessages.en.inbox }).getAttribute("href")).toBe("#selection-inbox");
    expect(document.getElementById("selection-inbox")).not.toBeNull();
    expect(nav.queryByRole("link", { name: selectionMessages.en.aggregates })).toBeNull();
    expect(nav.queryByRole("link", { name: selectionMessages.en.interviews })).toBeNull();
  });

  it("uses the localized label and includes management sections when permitted", async () => {
    mockWorkspace();
    render(<SelectionWorkspace org="org" actor="reviewer" locale="ta" permissions={["selection.assignment.manage", "selection.interview.manage"]} />);
    await screen.findByRole("heading", { name: selectionMessages.ta.interviews });
    const nav = within(screen.getByRole("navigation", { name: "பக்கப் பிரிவுகள்" }));
    expect(nav.getByRole("link", { name: selectionMessages.ta.aggregates }).getAttribute("href")).toBe("#selection-aggregates");
    expect(nav.getByRole("link", { name: selectionMessages.ta.interviews }).getAttribute("href")).toBe("#selection-interviews");
    expect(document.getElementById("selection-decisions")).not.toBeNull();
  });
});
