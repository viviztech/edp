import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import ApplicationHistory from "./history";

const org = "11111111-1111-4111-8111-111111111111";
const cycle = "22222222-2222-4222-8222-222222222222";
const first = "33333333-3333-4333-8333-333333333333";
const second = "44444444-4444-4444-8444-444444444444";
const entry = (id: string, name: string) => ({ id, organization_id: org, organization_name: name, cycle_id: cycle, cycle_code: "INTAKE", cycle_name_en: "Closed intake", cycle_name_ta: "முடிந்த சேர்க்கை", state: "under_review", version: 3, application_number: `EDP-${name}`, submitted_at: "2026-10-01T00:00:00Z", updated_at: "2026-10-02T00:00:00Z" });
const response = (body: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(body), { status }));
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("private application history", () => {
  it("keeps closed-intake status and validated destination available without open-cycle discovery", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response({ items: [entry(first, "Program A")], next_cursor: null })));
    render(<ApplicationHistory locale="en" refreshKey={0} canNavigate={() => true} />);
    const link = await screen.findByRole("link", { name: "View application" });
    expect(link.getAttribute("href")).toBe(`/en/applications?organization=${org}&cycle=${cycle}`);
    expect(screen.getByText("Current status: Under review")).toBeTruthy();
  });

  it("marks saved destinations unavailable while the current workspace is busy", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response({ items: [entry(first, "Program A")], next_cursor: null })));
    const view = render(<ApplicationHistory locale="en" refreshKey={0} canNavigate={() => true} navigationBlocked />);
    const link = await screen.findByRole("link", { name: "View application" });
    expect(link.getAttribute("aria-disabled")).toBe("true");
    const click = new MouseEvent("click", { bubbles: true, cancelable: true });
    fireEvent(link, click);
    expect(click.defaultPrevented).toBe(true);
    view.rerender(<ApplicationHistory locale="en" refreshKey={0} canNavigate={() => true} navigationBlocked={false} />);
    expect(link.getAttribute("aria-disabled")).toBe("false");
  });

  it("preserves earlier pages and retries the failed next-page cursor without duplicates", async () => {
    let attempts = 0;
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      if (String(input).includes("cursor=")) return ++attempts === 1 ? response({}, 503) : response({ items: [entry(first, "Program A"), entry(second, "Program B")], next_cursor: null });
      return response({ items: [entry(first, "Program A")], next_cursor: first });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<ApplicationHistory locale="en" refreshKey={0} canNavigate={() => true} />);
    await screen.findByText("Program A");
    fireEvent.click(screen.getByRole("button", { name: "More applications" }));
    await screen.findByRole("alert");
    expect(screen.getByText("Program A")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await screen.findByText("Program B");
    expect(screen.getAllByText("Program A")).toHaveLength(1);
    expect(fetchMock.mock.calls.filter(([url]) => String(url).includes(`cursor=${first}`))).toHaveLength(2);
    expect(screen.queryByRole("button", { name: "More applications" })).toBeNull();
  });

  it("does not turn a failed or malformed history response into an empty-history claim", async () => {
    const fetchMock = vi.fn().mockImplementationOnce(() => response({ csrf_token: "unexpected" })).mockImplementationOnce(() => response({ items: [], next_cursor: null }));
    vi.stubGlobal("fetch", fetchMock);
    render(<ApplicationHistory locale="en" refreshKey={0} canNavigate={() => true} />);
    await screen.findByRole("alert");
    expect(screen.queryByText("You have no saved applications yet.")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await screen.findByText("You have no saved applications yet.");
  });

  it("does not silently redirect a legacy form-only draft and honors cancelled navigation", async () => {
    const canNavigate = vi.fn(() => false);
    vi.stubGlobal("fetch", vi.fn(() => response({ items: [{ ...entry(first, "Legacy"), cycle_id: null, state: "draft" }, entry(second, "Program B")], next_cursor: null })));
    render(<ApplicationHistory locale="en" refreshKey={0} canNavigate={canNavigate} />);
    await screen.findByText("Legacy");
    expect(screen.getAllByRole("link")).toHaveLength(1);
    const link = screen.getByRole("link", { name: "View application" });
    const click = new MouseEvent("click", { bubbles: true, cancelable: true });
    fireEvent(link, click);
    expect(canNavigate).toHaveBeenCalledOnce();
    expect(click.defaultPrevented).toBe(true);
    await waitFor(() => expect(screen.getByText(/older draft/)).toBeTruthy());
  });

  it("blocks the previous cursor during refresh and ignores an older in-flight next page", async () => {
    let resolveOldPage!: (response: Response) => void;
    let resolveFreshPage!: (response: Response) => void;
    const fetchMock = vi.fn().mockImplementationOnce(() => response({ items: [entry(first, "Before refresh")], next_cursor: first }))
      .mockImplementationOnce(() => new Promise<Response>((resolve) => { resolveOldPage = resolve; }))
      .mockImplementationOnce(() => new Promise<Response>((resolve) => { resolveFreshPage = resolve; }));
    vi.stubGlobal("fetch", fetchMock);
    const view = render(<ApplicationHistory locale="en" refreshKey={0} canNavigate={() => true} />);
    await screen.findByText("Before refresh");
    fireEvent.click(screen.getByRole("button", { name: "More applications" }));
    view.rerender(<ApplicationHistory locale="en" refreshKey={1} canNavigate={() => true} />);
    const more = screen.getByRole("button", { name: "More applications" });
    expect((more as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(more);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    await act(async () => { resolveFreshPage(new Response(JSON.stringify({ items: [entry(second, "Fresh application")], next_cursor: null }))); });
    await screen.findByText("Fresh application");
    await act(async () => { resolveOldPage(new Response(JSON.stringify({ items: [entry(first, "Stale page")], next_cursor: first }))); });
    expect(screen.queryByText("Stale page")).toBeNull();
    expect(screen.queryByRole("button", { name: "More applications" })).toBeNull();
  });
});
