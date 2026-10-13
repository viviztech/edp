import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { DemoExperience } from "./demo-experience";
import { demoCopy } from "../lib/demo-copy";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function begin() {
  fireEvent.click(screen.getByRole("button", { name: "Start the demo" }));
  fireEvent.change(screen.getByLabelText("Demo display name"), {
    target: { value: "Sample Participant" },
  });
  fireEvent.submit(
    screen
      .getByRole("button", { name: "Create demo profile" })
      .closest("form")!,
  );
}

describe("isolated launch demonstration", () => {
  it("completes profile, draft, receipt, learning and mentoring without calling an API", () => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    vi.stubGlobal("requestAnimationFrame", () => 0);
    render(<DemoExperience locale="en" />);
    begin();
    const form = screen
      .getByRole("button", { name: "Submit demo application" })
      .closest("form")!;
    fireEvent.click(screen.getByRole("button", { name: "Save demo draft" }));
    expect(screen.getByRole("status").textContent).toContain(
      "saved for this browser tab",
    );
    fireEvent.submit(form);
    expect(screen.getByRole("status").textContent).toContain(
      "Complete the fields",
    );
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.submit(form);
    expect(screen.getByText(/^DEMO-/)).toBeTruthy();
    fireEvent.click(
      screen.getByRole("button", { name: "Open your demo space" }),
    );
    expect(screen.getByText("Welcome, Sample Participant")).toBeTruthy();
    fireEvent.click(
      screen.getByRole("button", { name: "Learning" }),
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Mark practice lesson complete" }),
    );
    expect(
      screen
        .getByRole("button", { name: "Practice lesson completed" })
        .hasAttribute("disabled"),
    ).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Overview" }));
    expect(screen.getByText("Practice progress: 1 / 3")).toBeTruthy();
    fireEvent.click(
      screen.getByRole("button", { name: "Mentoring" }),
    );
    fireEvent.change(screen.getByLabelText("Sample appointment"), {
      target: { value: "1" },
    });
    fireEvent.submit(
      screen
        .getByRole("button", { name: "Save demo appointment" })
        .closest("form")!,
    );
    expect(screen.getByRole("status").textContent).toBe(
      "Demo appointment saved",
    );
    fireEvent.click(screen.getByRole("button", { name: "Overview" }));
    expect(screen.getByText("21 Oct · 2:00 PM")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Restart demo" }));
    expect(screen.getByRole("button", { name: "Start the demo" })).toBeTruthy();
    expect(screen.queryByText(/^DEMO-/)).toBeNull();
    expect(fetch).not.toHaveBeenCalled();
  });
  it("provides the same sample-only journey in Tamil", () => {
    vi.stubGlobal("requestAnimationFrame", () => 0);
    expect(Object.keys(demoCopy.en).sort()).toEqual(
      Object.keys(demoCopy.ta).sort(),
    );
    render(<DemoExperience locale="ta" />);
    fireEvent.click(screen.getByRole("button", { name: demoCopy.ta.start }));
    expect(
      (screen.getByLabelText(demoCopy.ta.email) as HTMLInputElement).readOnly,
    ).toBe(true);
    fireEvent.submit(
      screen
        .getByRole("button", { name: demoCopy.ta.accountAction })
        .closest("form")!,
    );
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.submit(
      screen.getByRole("button", { name: demoCopy.ta.submit }).closest("form")!,
    );
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe(
      demoCopy.ta.receiptTitle,
    );
  });
});
