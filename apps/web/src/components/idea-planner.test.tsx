import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { IdeaPlanner } from "./idea-planner";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
describe("private idea planner", () => {
  it("does not download an empty worksheet and updates progress when an answer is entered", () => {
    render(<IdeaPlanner locale="en" />);
    fireEvent.submit(
      screen
        .getByRole("button", { name: "Download your plan" })
        .closest("form")!,
    );
    expect(screen.getByRole("status").textContent).toBe(
      "Add an answer to start your plan.",
    );
    fireEvent.change(
      screen.getByLabelText("What is your idea?", { exact: false }),
      { target: { value: "Sample idea" } },
    );
    expect(screen.getByRole("progressbar").getAttribute("value")).toBe("1");
    vi.spyOn(window, "confirm").mockReturnValue(true);
    fireEvent.click(screen.getByRole("button", { name: "Clear answers" }));
    expect(screen.getByRole("progressbar").getAttribute("value")).toBe("0");
  });
  it("warns on browser navigation while answers are unsaved", () => {
    render(<IdeaPlanner locale="en" />);
    fireEvent.change(screen.getByLabelText("What is your idea?", { exact: false }), { target: { value: "Sample idea" } });
    const event = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    fireEvent.click(screen.getByRole("button", { name: "Clear answers" }));
    const cleared = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(cleared);
    expect(cleared.defaultPrevented).toBe(false);
  });
});
