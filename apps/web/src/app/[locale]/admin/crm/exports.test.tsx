import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { components } from "../../../../lib/api-contracts";
import { crmExportMessages } from "../../../../lib/crm-export-messages";
import CrmExports from "./exports";
import CrmWorkspace from "./view";

const org = "11111111-1111-4111-8111-111111111111", id = "22222222-2222-4222-8222-222222222222";
const root = `/api/crm/organizations/${org}/exports`;
type ExportJob = components["schemas"]["ExportJobView"];
const job = (status: ExportJob["status"] = "queued", extra: Partial<ExportJob> = {}): ExportJob => ({
  id, status, row_count: 0, error_code: "", completed_at: null,
  expires_at: new Date(Date.now() + 3600000).toISOString(), ...extra,
});
const json = (value: unknown, status = 200) => Response.json(value, { status });
const historyUrl = root + "?limit=25";
const batch = (items: ExportJob[] = [], next_cursor: string | null = null) => json({ items, next_cursor });
function stubFetch(mock: (url: string, init?: RequestInit) => Promise<Response>) {
  // The original command/status cases start with an empty authorized history.
  // History-specific cases below exercise actual list requests and failures.
  vi.stubGlobal("fetch", (url: string, init?: RequestInit) => url === historyUrl ? Promise.resolve(batch()) : mock(url, init));
}
async function click(name: string) {
  await act(async () => {});
  await act(async () => { fireEvent.click(screen.getByRole("button", { name })); });
}
afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("CRM export recovery", () => {
  it("retains an accepted durable queue request, polls reads only, and offers the authorized CSV only after completion", async () => {
    vi.useFakeTimers();
    let checks = 0;
    const mock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url === "/api/session/csrf") return json({ csrf_token: "csrf-from-endpoint" });
      if (init?.method === "POST") return json(job(), 202);
      return json(++checks === 1 ? job("running") : job("completed", { row_count: 42 }));
    });
    stubFetch(mock); render(<CrmExports org={org} locale="en" />);
    await click(crmExportMessages.en.request);
    expect(screen.getByText(crmExportMessages.en.queuedHint)).toBeTruthy();
    expect(screen.getByRole("button", { name: crmExportMessages.en.request })).toHaveProperty("disabled", true);
    expect(screen.queryByRole("link")).toBeNull();
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    expect(screen.getByText(crmExportMessages.en.runningHint)).toBeTruthy();
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    expect(screen.getByText("Rows: 42")).toBeTruthy();
    expect(screen.getByRole("link", { name: crmExportMessages.en.download }).getAttribute("href")).toBe(`${root}/${id}/download`);
    expect(mock.mock.calls.filter(call => call[1]?.method === "POST")).toEqual([[root, expect.objectContaining({ body: "{}", headers: { "Content-Type": "application/json", "x-csrf-token": "csrf-from-endpoint" } })]]);
    expect(mock.mock.calls.filter(call => call[0] === `${root}/${id}`)).toHaveLength(2);
    await act(async () => { await vi.advanceTimersByTimeAsync(30000); });
    expect(checks).toBe(2);
  });

  it("does not duplicate an outstanding creation even before its first response", async () => {
    let finish!: (response: Response) => void;
    const pending = new Promise<Response>(resolve => { finish = resolve; });
    const mock = vi.fn(async (url: string) => url === "/api/session/csrf" ? json({ csrf_token: "csrf" }) : pending);
    stubFetch(mock); render(<CrmExports org={org} locale="en" />);
    await act(async () => {});
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: crmExportMessages.en.request }));
      fireEvent.click(screen.getByRole("button", { name: crmExportMessages.en.request }));
    });
    expect(mock.mock.calls.filter(call => call[0] === root)).toHaveLength(1);
    await act(async () => { finish(json(job(), 202)); });
    expect(screen.getByText(crmExportMessages.en.queuedHint)).toBeTruthy();
  });

  it.each(["network", "server", "malformed"])("warns after an uncertain %s response and creates another job only through the explicit separate-request action", async mode => {
    vi.useFakeTimers(); let posts = 0;
    const mock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url === "/api/session/csrf") return json({ csrf_token: "csrf" });
      if (init?.method === "POST" && ++posts === 1) {
        if (mode === "server") return json({}, 503);
        if (mode === "malformed") return json({ status: "completed" }, 202);
        throw new Error("Lost after commit");
      }
      return json(job("completed"), 202);
    });
    stubFetch(mock); render(<CrmExports org={org} locale="en" />);
    await click(crmExportMessages.en.request);
    expect(screen.getByRole("alert").textContent).toBe(crmExportMessages.en.uncertain);
    expect(screen.getByRole("button", { name: crmExportMessages.en.request })).toHaveProperty("disabled", true);
    await act(async () => { await vi.advanceTimersByTimeAsync(60000); });
    expect(posts).toBe(1); expect(mock.mock.calls.some(call => call[0] === `${root}/${id}`)).toBe(false);
    await click(crmExportMessages.en.separate);
    expect(posts).toBe(2); expect(screen.getByRole("link", { name: crmExportMessages.en.download })).toBeTruthy();
  });

  it("allows a safe retry when the CSRF endpoint failed before any export command", async () => {
    const mock = vi.fn(async () => json({}, 503)); stubFetch(mock);
    render(<CrmExports org={org} locale="en" />); await click(crmExportMessages.en.request);
    expect(mock.mock.calls).toHaveLength(1); expect(mock.mock.calls[0]).toEqual(["/api/session/csrf", { cache: "no-store" }]);
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.getByText(crmExportMessages.en.requestFailed)).toBeTruthy();
    expect(screen.getByRole("button", { name: crmExportMessages.en.request })).toHaveProperty("disabled", false);
  });

  it("treats a definitive pre-creation configuration rejection as unavailable rather than an uncertain committed request", async () => {
    const mock = vi.fn(async (url: string) => url === historyUrl ? batch() : url === "/api/session/csrf" ? json({ csrf_token: "csrf" })
      : json({ error: { code: "export_retention_unconfigured", message: "Private configuration details" } }, 503));
    vi.stubGlobal("fetch", mock); render(<CrmExports org={org} locale="en" />); await click(crmExportMessages.en.request);
    expect(screen.getByText(crmExportMessages.en.unavailable)).toBeTruthy();
    expect(screen.queryByRole("alert")).toBeNull(); expect(screen.queryByText("Private configuration details")).toBeNull();
    expect(screen.getByRole("button", { name: crmExportMessages.en.request })).toHaveProperty("disabled", false);
    expect(mock.mock.calls.filter(call => call[0] === historyUrl)).toHaveLength(1);
  });

  it.each([401, 403, 404, 503])("removes the stale completed download after a %s status-read failure and recovers only by reading that same job", async status => {
    let checks = 0;
    const mock = vi.fn(async (url: string, init?: RequestInit) => url === "/api/session/csrf" ? json({ csrf_token: "csrf" })
      : init?.method === "POST" || ++checks > 1 ? json(job("completed", { row_count: 3 })) : json({}, status));
    stubFetch(mock); render(<CrmExports org={org} locale="en" />);
    await click(crmExportMessages.en.request); expect(screen.getByRole("link")).toBeTruthy();
    await click(crmExportMessages.en.check);
    expect(screen.queryByRole("link")).toBeNull(); expect(screen.getByText(id)).toBeTruthy();
    expect(screen.getByText(status === 401 ? crmExportMessages.en.sessionExpired : status === 503 ? crmExportMessages.en.checkFailed : crmExportMessages.en.noAccess)).toBeTruthy();
    await click(crmExportMessages.en.check);
    expect(screen.getByRole("link").getAttribute("href")).toBe(`${root}/${id}/download`);
    expect(mock.mock.calls.filter(call => call[1]?.method === "POST")).toHaveLength(1);
  });

  it("expires a completed download without waiting for another user action", async () => {
    vi.useFakeTimers(); const expires = new Date(Date.now() + 1000).toISOString();
    stubFetch(vi.fn(async (url: string) => json(url === "/api/session/csrf" ? { csrf_token: "csrf" } : job("completed", { expires_at: expires }))));
    render(<CrmExports org={org} locale="en" />); await click(crmExportMessages.en.request);
    expect(screen.getByRole("link")).toBeTruthy();
    await act(async () => { await vi.advanceTimersByTimeAsync(1001); });
    expect(screen.queryByRole("link")).toBeNull(); expect(screen.getByText(crmExportMessages.en.expiredHint)).toBeTruthy();
    expect(screen.getByRole("button", { name: crmExportMessages.en.request })).toHaveProperty("disabled", false);
  });

  it("bounds automatic checks and continues through an explicit manual read", async () => {
    vi.useFakeTimers(); let checks = 0;
    const mock = vi.fn(async (url: string, init?: RequestInit) => url === "/api/session/csrf" ? json({ csrf_token: "csrf" })
      : init?.method === "POST" ? json(job(), 202) : json(++checks > 20 ? job("completed") : job("queued", { error_code: "recovered_lease" })));
    stubFetch(mock); render(<CrmExports org={org} locale="en" />); await click(crmExportMessages.en.request);
    for (let index = 0; index < 20; index++) await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    expect(checks).toBe(20); expect(screen.getByText(crmExportMessages.en.paused)).toBeTruthy();
    expect(screen.getByText(crmExportMessages.en.retryHint)).toBeTruthy();
    await act(async () => { await vi.advanceTimersByTimeAsync(30000); }); expect(checks).toBe(20);
    await click(crmExportMessages.en.check); expect(checks).toBe(21); expect(screen.getByRole("link")).toBeTruthy();
  });

  it.each(["retry_exhausted", "requester_unavailable", "row_limit_exceeded", "unexpected_private_details"])("shows a safe terminal reason for %s without exposing raw diagnostics", async errorCode => {
    stubFetch(vi.fn(async (url: string) => json(url === "/api/session/csrf" ? { csrf_token: "csrf" } : job("failed", { error_code: errorCode }))));
    render(<CrmExports org={org} locale="en" />); await click(crmExportMessages.en.request);
    const expected = errorCode === "retry_exhausted" ? crmExportMessages.en.retryExhausted : errorCode === "requester_unavailable" ? crmExportMessages.en.requesterUnavailable
      : errorCode === "row_limit_exceeded" ? crmExportMessages.en.tooLarge : crmExportMessages.en.failedHint;
    expect(screen.getByText(expected)).toBeTruthy(); expect(screen.queryByText(errorCode)).toBeNull();
    expect(screen.queryByRole("link")).toBeNull(); expect(screen.getByRole("button", { name: crmExportMessages.en.request })).toHaveProperty("disabled", false);
  });

  it("cancels future polling on unmount and respects a blocked workspace", async () => {
    vi.useFakeTimers();
    const mock = vi.fn(async (url: string) => json(url === "/api/session/csrf" ? { csrf_token: "csrf" } : job())); stubFetch(mock);
    const { rerender, unmount } = render(<CrmExports org={org} locale="en" blocked />);
    fireEvent.click(screen.getByRole("button", { name: crmExportMessages.en.request })); expect(mock).not.toHaveBeenCalled();
    rerender(<CrmExports org={org} locale="en" />); await click(crmExportMessages.en.request);
    unmount(); await act(async () => { await vi.advanceTimersByTimeAsync(60000); });
    expect(mock.mock.calls).toHaveLength(2);
  });

  it("keeps localized labels aligned and renders the Tamil queue without raw status enums", async () => {
    expect(Object.keys(crmExportMessages.en).sort()).toEqual(Object.keys(crmExportMessages.ta).sort());
    stubFetch(vi.fn(async (url: string) => json(url === "/api/session/csrf" ? { csrf_token: "csrf" } : job())));
    render(<CrmExports org={org} locale="ta" />); await click(crmExportMessages.ta.request);
    expect(screen.getByRole("region", { name: crmExportMessages.ta.title })).toBeTruthy();
    expect(screen.getByText(crmExportMessages.ta.queued)).toBeTruthy(); expect(screen.queryByText("queued")).toBeNull();
  });

  it("keeps the export journey hidden without the existing CRM export permission", async () => {
    const requested: string[] = [];
    const mock = vi.fn(async (url: string) => { requested.push(url); return json({ items: [], next_cursor: null }); }); vi.stubGlobal("fetch", mock);
    render(<CrmWorkspace org={org} locale="en" permissions={["crm.lead.view"]} />);
    await waitFor(() => expect(mock).toHaveBeenCalled());
    expect(screen.queryByRole("region", { name: crmExportMessages.en.title })).toBeNull();
    expect(requested.some(url => url.includes("/exports"))).toBe(false);
  });

  it("recovers an owned export after reload through bounded history and explicit reauthorized selection", async () => {
    const completed = job("completed", { row_count: 7, created_at: new Date(Date.now() - 60000).toISOString() });
    const mock = vi.fn(async (url: string) => url === historyUrl ? batch([completed]) : json(completed));
    vi.stubGlobal("fetch", mock);
    const first = render(<CrmExports org={org} locale="en" />);
    await click(`${crmExportMessages.en.open}: ${id}`);
    expect(screen.getByRole("link").getAttribute("href")).toBe(`${root}/${id}/download`);
    first.unmount();
    render(<CrmExports org={org} locale="en" />); await act(async () => {});
    expect(screen.queryByRole("link")).toBeNull();
    expect(within(screen.getByRole("group", { name: crmExportMessages.en.selected })).queryByText(id)).toBeNull();
    await click(`${crmExportMessages.en.open}: ${id}`);
    expect(screen.getByRole("link").getAttribute("href")).toBe(`${root}/${id}/download`);
    expect(mock.mock.calls.filter(call => call[0] === historyUrl)).toHaveLength(2);
    expect(mock.mock.calls.filter(call => call[0] === `${root}/${id}`)).toHaveLength(2);
    expect(mock.mock.calls.every(call => call[0] !== "/api/session/csrf")).toBe(true);
  });

  it("recovers a lost committed POST through history without guessing which request to select or repeating the command", async () => {
    const olderId = "33333333-3333-4333-8333-333333333333";
    let posted = false;
    const mock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url === historyUrl) return posted ? batch([job(), job("completed", { id: olderId })]) : batch();
      if (url === "/api/session/csrf") return json({ csrf_token: "csrf" });
      if (init?.method === "POST") { posted = true; throw new Error("Lost after commit"); }
      return json(job("completed", { id: olderId }));
    });
    vi.stubGlobal("fetch", mock); render(<CrmExports org={org} locale="en" />);
    await click(crmExportMessages.en.request);
    expect(screen.getByRole("alert").textContent).toBe(crmExportMessages.en.uncertain);
    expect(screen.getByRole("button", { name: `${crmExportMessages.en.open}: ${id}` })).toBeTruthy();
    expect(mock.mock.calls.some(call => call[0] === `${root}/${id}` || call[0] === `${root}/${olderId}`)).toBe(false);
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.getByRole("button", { name: crmExportMessages.en.separate })).toHaveProperty("disabled", true);
    await click(`${crmExportMessages.en.open}: ${olderId}`);
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.getByRole("link").getAttribute("href")).toBe(`${root}/${olderId}/download`);
    expect(mock.mock.calls.filter(call => call[1]?.method === "POST")).toHaveLength(1);
    expect(mock.mock.calls.filter(call => call[0] === historyUrl)).toHaveLength(2);
  });

  it("preserves loaded history and the exact cursor after failed continuation, without duplicating repeated entries", async () => {
    const next = "33333333-3333-4333-8333-333333333333"; let pages = 0;
    const mock = vi.fn(async (url: string) => {
      if (url === historyUrl) return batch([job("completed")], id);
      return ++pages === 1 ? json({}, 503) : batch([job("completed"), job("failed", { id: next })]);
    });
    vi.stubGlobal("fetch", mock); render(<CrmExports org={org} locale="en" />);
    await click(crmExportMessages.en.moreHistory);
    expect(screen.getByRole("button", { name: `${crmExportMessages.en.open}: ${id}` })).toBeTruthy();
    expect(screen.getByText(crmExportMessages.en.historyFailed)).toBeTruthy();
    await click(crmExportMessages.en.moreHistory);
    expect(screen.getAllByRole("button", { name: `${crmExportMessages.en.open}: ${id}` })).toHaveLength(1);
    expect(screen.getByRole("button", { name: `${crmExportMessages.en.open}: ${next}` })).toBeTruthy();
    expect(mock.mock.calls.filter(call => call[0] === `${historyUrl}&cursor=${id}`)).toHaveLength(2);
    expect(screen.queryByRole("button", { name: crmExportMessages.en.moreHistory })).toBeNull();
  });

  it.each([401, 403])("clears selected download and history on a %s history response, then requires fresh selection after recovery", async status => {
    let lists = 0;
    const mock = vi.fn(async (url: string) => url === historyUrl && ++lists === 2 ? json({}, status)
      : url === historyUrl ? batch([job("completed")]) : json(job("completed")));
    vi.stubGlobal("fetch", mock); render(<CrmExports org={org} locale="en" />);
    await click(`${crmExportMessages.en.open}: ${id}`); expect(screen.getByRole("link")).toBeTruthy();
    await click(crmExportMessages.en.refreshHistory);
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.queryByRole("button", { name: `${crmExportMessages.en.open}: ${id}` })).toBeNull();
    expect(screen.getByRole("button", { name: crmExportMessages.en.request })).toHaveProperty("disabled", true);
    await click(crmExportMessages.en.refreshHistory); expect(screen.queryByRole("link")).toBeNull();
    await click(`${crmExportMessages.en.open}: ${id}`); expect(screen.getByRole("link")).toBeTruthy();
  });

  it("never trusts a history item as download authorization after its detail returns forbidden", async () => {
    const mock = vi.fn(async (url: string) => url === historyUrl ? batch([job("completed")]) : json({}, 403));
    vi.stubGlobal("fetch", mock); render(<CrmExports org={org} locale="en" />);
    await click(`${crmExportMessages.en.open}: ${id}`);
    expect(screen.getByText(crmExportMessages.en.noAccess)).toBeTruthy(); expect(screen.queryByRole("link")).toBeNull();
    expect(within(screen.getByRole("group", { name: crmExportMessages.en.selected })).queryByText(id)).toBeNull();
  });

  it("does not restore a download from a late status response after a newer history denial", async () => {
    let finishHistory!: (response: Response) => void, finishDetail!: (response: Response) => void;
    const lateHistory = new Promise<Response>(resolve => { finishHistory = resolve; });
    const lateDetail = new Promise<Response>(resolve => { finishDetail = resolve; });
    let lists = 0, details = 0;
    const mock = vi.fn(async (url: string) => url === historyUrl ? ++lists === 1 ? batch([job("completed")]) : lateHistory
      : ++details === 1 ? json(job("completed")) : lateDetail);
    vi.stubGlobal("fetch", mock); render(<CrmExports org={org} locale="en" />);
    await click(`${crmExportMessages.en.open}: ${id}`); expect(screen.getByRole("link")).toBeTruthy();
    await click(crmExportMessages.en.refreshHistory); await click(crmExportMessages.en.check);
    await act(async () => { finishHistory(json({}, 403)); });
    expect(screen.queryByRole("link")).toBeNull();
    await act(async () => { finishDetail(json(job("completed"))); });
    expect(screen.queryByRole("link")).toBeNull();
    expect(within(screen.getByRole("group", { name: crmExportMessages.en.selected })).queryByText(id)).toBeNull();
  });

  it("requires a successful initial history read before creating a new export", async () => {
    let lists = 0;
    const mock = vi.fn(async (url: string) => url === historyUrl && ++lists === 1 ? json({}, 503)
      : url === historyUrl ? batch() : url === "/api/session/csrf" ? json({ csrf_token: "csrf" }) : json(job(), 202));
    vi.stubGlobal("fetch", mock); render(<CrmExports org={org} locale="en" />);
    await click(crmExportMessages.en.request);
    expect(screen.getByText(crmExportMessages.en.historyFailed)).toBeTruthy();
    expect(mock.mock.calls).toHaveLength(1);
    await click(crmExportMessages.en.refreshHistory); await click(crmExportMessages.en.request);
    expect(screen.getByText(crmExportMessages.en.queuedHint)).toBeTruthy();
  });
});
