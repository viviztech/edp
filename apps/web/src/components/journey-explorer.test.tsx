import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { JourneyExplorer } from "./journey-explorer";
import { landingCopy } from "../lib/landing-copy";

afterEach(cleanup);

describe("public journey navigation", () => {
  it("changes the visible guidance and destination when a visitor selects a stage", () => {
    render(
      <JourneyExplorer
        locale="en"
        label={landingCopy.en.journeyLabel}
        stages={landingCopy.en.stages}
      />,
    );
    fireEvent.click(screen.getByRole("tab", { name: /Plan & grow/ }));
    expect(screen.getByRole("tabpanel").getAttribute("aria-labelledby")).toBe(
      "journey-tab-3",
    );
    expect(
      screen
        .getByRole("link", { name: /See the available resources/ })
        .getAttribute("href"),
    ).toBe("/en/pages/resources");
    expect(
      screen.queryByRole("link", { name: /Get to know the program/ }),
    ).toBeNull();
  });

  it("supports arrow keys and endpoint shortcuts with focus following selection", () => {
    render(
      <JourneyExplorer
        locale="en"
        label={landingCopy.en.journeyLabel}
        stages={landingCopy.en.stages}
      />,
    );
    const tabs = screen.getAllByRole("tab");
    fireEvent.keyDown(tabs[0], { key: "ArrowDown" });
    expect(document.activeElement).toBe(tabs[1]);
    expect(tabs[1].getAttribute("aria-selected")).toBe("true");
    fireEvent.keyDown(tabs[1], { key: "End" });
    expect(document.activeElement).toBe(tabs[3]);
    fireEvent.keyDown(tabs[3], { key: "ArrowRight" });
    expect(document.activeElement).toBe(tabs[0]);
    fireEvent.keyDown(tabs[0], { key: "ArrowUp" });
    expect(document.activeElement).toBe(tabs[3]);
    fireEvent.keyDown(tabs[3], { key: "Home" });
    expect(document.activeElement).toBe(tabs[0]);
  });

  it("keeps the selected guidance and next-step link in Tamil", () => {
    render(
      <JourneyExplorer
        locale="ta"
        label={landingCopy.ta.journeyLabel}
        stages={landingCopy.ta.stages}
      />,
    );
    fireEvent.click(screen.getAllByRole("tab")[1]);
    expect(screen.getByRole("link").getAttribute("href")).toBe(
      "/ta/pages/apply",
    );
    expect(screen.getByRole("tabpanel").textContent).toContain("உங்கள் கதை.");
  });
});
