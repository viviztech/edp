import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import BusinessStaff from "./view";

const org = "11111111-1111-4111-8111-111111111111";
const root = `/api/businesses/organizations/${org}`;
const dashboard = { policy: { day_offsets: [5, 30], version: 1 }, profiles: [] };
const response = (body: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(body), { status }));
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("business follow-up administration", () => {
  it("keeps a read-only viewer from changing the schedule", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response(dashboard)));
    render(<BusinessStaff org={org} locale="en" canManage={false} />);
    await screen.findByText("No business profiles yet.");
    expect(screen.queryByRole("button", { name: "Save schedule" })).toBeNull();
    expect(screen.queryByLabelText("Reason for change")).toBeNull();
  });

  it("preserves the schedule and reason through conflict, refreshes the version, and freezes the write", async () => {
    let version = 1;
    let release: (() => void) | undefined;
    const writes: unknown[] = [];
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      if (String(input) === "/api/session/csrf") return response({ csrf_token: "csrf" });
      if (String(input) === root + "/staff") return response({ ...dashboard, policy: { ...dashboard.policy, version } });
      if (String(input) === root + "/policy") {
        const body = JSON.parse(String(init?.body)); writes.push(body);
        if (writes.length === 1) { version = 2; return response({}, 409); }
        return new Promise((resolve) => { release = () => resolve(new Response(JSON.stringify({ day_offsets: [7, 45], version: 3 }))); });
      }
      throw new Error("unexpected_request");
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<BusinessStaff org={org} locale="en" canManage />);
    fireEvent.change(await screen.findByLabelText("Follow-up days"), { target: { value: "7, 45" } });
    fireEvent.change(screen.getByLabelText("Reason for change"), { target: { value: "New cohort schedule" } });
    fireEvent.click(screen.getByRole("button", { name: "Save schedule" }));
    await screen.findByText("Refresh saved schedule before another save. Your input is kept.");
    expect((screen.getByRole("button", { name: "Save schedule" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Refresh saved schedule" }));
    await screen.findByText("Saved schedule refreshed. Compare your input before saving.");
    expect((screen.getByLabelText("Follow-up days") as HTMLInputElement).value).toBe("7, 45");
    expect((screen.getByLabelText("Reason for change") as HTMLInputElement).value).toBe("New cohort schedule");
    fireEvent.click(screen.getByRole("button", { name: "Save schedule" }));
    await waitFor(() => expect(release).toBeDefined());
    expect((screen.getByLabelText("Reason for change").closest("fieldset") as HTMLFieldSetElement).disabled).toBe(true);
    release!();
    await screen.findByText("Schedule saved.");
    expect(writes).toEqual([
      { expected_version: 1, day_offsets: [7, 45], reason: "New cohort schedule" },
      { expected_version: 2, day_offsets: [7, 45], reason: "New cohort schedule" },
    ]);
  });
});
