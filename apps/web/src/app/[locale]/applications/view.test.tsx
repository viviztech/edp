import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import ApplicationWorkspace from "./view";
import Link from "next/link";

const form = {
  id: "22222222-2222-4222-8222-222222222222",
  organization_id: "11111111-1111-4111-8111-111111111111",
  version: 1,
  title_en: "Enterprise application",
  title_ta: "Tamil application",
  fields: [{
    id: "33333333-3333-4333-8333-333333333333", key: "business_idea", section: "proposal",
    label_en: "Business idea", label_ta: "Tamil business idea", field_type: "text" as const,
    required: true, position: 1,
  }],
  acknowledgements: [{
    id: "44444444-4444-4444-8444-444444444444", key: "final_declaration", kind: "declaration" as const,
    label_en: "I declare this is accurate.", label_ta: "Tamil declaration", required: true, position: 1,
  }, {
    id: "55555555-5555-4555-8555-555555555555", key: "application_consent", kind: "consent" as const,
    label_en: "I consent to processing.", label_ta: "Tamil consent", required: true, position: 2,
  }],
};
const cycle = {
  id: "66666666-6666-4666-8666-666666666666", code: "2026-A", name_en: "2026 intake", name_ta: "Tamil intake",
  form_id: form.id, opens_at: "2026-09-01T00:00:00Z", closes_at: "2026-10-01T00:00:00Z",
};
const draft = { id: "77777777-7777-4777-8777-777777777777", cycle_id: cycle.id, form, state: "draft" as const, version: 1, revision: 1, completion_percent: 0, answers: [], updated_at: "2026-09-23T00:00:00Z" };

function response(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));
}

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("application final submission", () => {
  it("saves answers and accepted policy before showing the immutable receipt", async () => {
    const calls: Array<{ url: string; method: string; body?: string }> = [];
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); const method = init?.method ?? "GET";
      calls.push({ url, method, body: typeof init?.body === "string" ? init.body : undefined });
      if (url.endsWith("/cycles")) return response({ items: [cycle] });
      if (url.endsWith(`/cycles/${cycle.id}/application`)) return response(draft);
      if (url === "/api/session/csrf") return response({ csrf_token: "test-csrf" });
      if (method === "PATCH") return response({ ...draft, version: 2, revision: 2, completion_percent: 100, answers: [{ field_id: form.fields[0].id, value: "A repair service" }] });
      if (url.endsWith("/submit")) return response({ ...draft, state: "submitted", version: 3, revision: 2, completion_percent: 100, application_number: "EDP-2026-00000001", submitted_at: "2026-09-23T01:00:00Z", answers: [{ field_id: form.fields[0].id, value: "A repair service" }], accepted_acknowledgements: form.acknowledgements.map((item) => ({ definition_id: item.id, accepted_at: "2026-09-23T01:00:00Z" })), status_history: [{ from_state: "draft", to_state: "submitted", application_version: 3, reason_code: "applicant_submitted", created_at: "2026-09-23T01:00:00Z" }], updated_at: "2026-09-23T01:00:00Z" });
      return response({ error: { code: "unexpected" } }, 500);
    }));
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<ApplicationWorkspace locale="en" org={form.organization_id} />);
    fireEvent.change(await screen.findByLabelText("Business idea *"), { target: { value: "A repair service" } });
    fireEvent.click(screen.getByLabelText(/I declare this is accurate/));
    fireEvent.click(screen.getByLabelText(/I consent to processing/));
    fireEvent.click(screen.getByRole("button", { name: "Submit application" }));

    expect(await screen.findByText(/EDP-2026-00000001/)).toBeTruthy();
    await waitFor(() => expect(calls.some((call) => call.method === "PATCH")).toBe(true));
    const submission = calls.find((call) => call.url.endsWith("/submit"));
    expect(submission?.body).toContain('"expected_version":2');
    expect(submission?.body).toContain(form.acknowledgements[1].id);
  });

  it("blocks final submission until every required acknowledgement is accepted", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/cycles")) return response({ items: [cycle] });
      if (url.endsWith(`/cycles/${cycle.id}/application`)) return response(draft);
      return response({ csrf_token: "test-csrf" });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<ApplicationWorkspace locale="en" org={form.organization_id} />);
    fireEvent.change(await screen.findByLabelText("Business idea *"), { target: { value: "A repair service" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit application" }));
    expect(await screen.findByText("Accept the required declarations and consent before submitting.")).toBeTruthy();
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/submit"))).toBe(false);
  });

  it("reconciles history and receipt when a successful submission response was lost", async () => {
    let committed = false;
    const submitted = { ...draft, state: "submitted", version: 3, completion_percent: 100, application_number: "EDP-2026-00000001", submitted_at: "2026-09-23T01:00:00Z", accepted_acknowledgements: [], status_history: [], answers: [{ field_id: form.fields[0].id, value: "A repair service" }] };
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.startsWith("/api/applications/mine")) return response({ items: [{ id: draft.id, organization_id: form.organization_id, organization_name: "Saved program", cycle_id: cycle.id, cycle_name_en: cycle.name_en, state: committed ? "submitted" : "draft", updated_at: draft.updated_at }], next_cursor: null });
      if (url.endsWith("/cycles")) return response({ items: [cycle] });
      if (url.endsWith(`/cycles/${cycle.id}/application`)) return response(committed ? submitted : draft);
      if (url === "/api/session/csrf") return response({ csrf_token: "test-csrf" });
      if (init?.method === "PATCH") return response({ ...draft, version: 2, answers: submitted.answers });
      if (url.endsWith("/submit")) { committed = true; return response({}, 503); }
      return response({}, 500);
    }));
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<ApplicationWorkspace locale="en" org={form.organization_id} />);
    fireEvent.change(await screen.findByLabelText("Business idea *"), { target: { value: "A repair service" } });
    fireEvent.click(screen.getByLabelText(/I declare this is accurate/));
    fireEvent.click(screen.getByLabelText(/I consent to processing/));
    fireEvent.click(screen.getByRole("button", { name: "Submit application" }));
    await screen.findByText(/The request could not be completed/);
    expect(screen.getByText("Current status: Draft")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Reload application" }));
    expect(await screen.findByText("Current status: Submitted")).toBeTruthy();
    expect(await screen.findByText(/Application number: EDP-2026-00000001/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Submit application" })).toBeNull();
  });
});

describe("saved intake recovery", () => {
  function mockWorkspace(options: { discoveryFails?: boolean; open?: boolean; missing?: boolean; state?: "draft" | "under_review" } = {}) {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.startsWith("/api/applications/mine")) return response({ items: [], next_cursor: null });
      if (url.endsWith("/cycles")) return options.discoveryFails ? response({}, 503) : response({ items: options.open ? [cycle] : [] });
      if (url.endsWith(`/cycles/${cycle.id}/application`)) {
        if (options.missing) return response({ error: { code: "not_found" } }, 404);
        return response(options.state === "under_review" ? {
          ...draft, state: "under_review", application_number: "EDP-2026-00000001", submitted_at: "2026-09-23T01:00:00Z",
          accepted_acknowledgements: [], status_history: [],
        } : draft);
      }
      return response({}, 500);
    });
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
  }

  it("opens a saved closed intake as read-only without substituting an open intake", async () => {
    mockWorkspace();
    render(<ApplicationWorkspace locale="en" org={form.organization_id} initialCycle={cycle.id} />);
    const field = await screen.findByLabelText("Business idea *");
    expect((field as HTMLInputElement).disabled).toBe(true);
    expect(screen.getByText(/This intake is closed/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Save draft" })).toBeNull();
  });

  it("keeps applications under review immutable even while their intake is open", async () => {
    mockWorkspace({ open: true, state: "under_review" });
    render(<ApplicationWorkspace locale="en" org={form.organization_id} initialCycle={cycle.id} />);
    expect((await screen.findByLabelText("Business idea *") as HTMLInputElement).disabled).toBe(true);
    expect(screen.getByText(/EDP-2026-00000001/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Submit application" })).toBeNull();
  });

  it("distinguishes failed discovery from a closed intake while preserving the saved view", async () => {
    mockWorkspace({ discoveryFails: true });
    render(<ApplicationWorkspace locale="en" org={form.organization_id} initialCycle={cycle.id} />);
    expect(await screen.findByLabelText("Business idea *")).toBeTruthy();
    expect(screen.getByText(/The request could not be completed/)).toBeTruthy();
    expect(screen.queryByText(/This intake is closed/)).toBeNull();
    expect(screen.queryByText(/No application cycle is open/)).toBeNull();
  });

  it("does not open another intake when the explicit saved intake is unavailable", async () => {
    const fetchMock = mockWorkspace({ open: true, missing: true });
    const missing = "88888888-8888-4888-8888-888888888888";
    render(<ApplicationWorkspace locale="en" org={form.organization_id} initialCycle={missing} />);
    expect(await screen.findByText(/The selected application is unavailable/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Start application" })).toBeNull();
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith(`/cycles/${cycle.id}/application`))).toBe(false);
  });

  it("preserves unsaved answers when the applicant cancels reloading", async () => {
    mockWorkspace({ open: true });
    vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<ApplicationWorkspace locale="en" org={form.organization_id} />);
    const field = await screen.findByLabelText("Business idea *");
    fireEvent.change(field, { target: { value: "Unsaved repair service" } });
    fireEvent.click(screen.getByRole("button", { name: "Reload application" }));
    expect(window.confirm).toHaveBeenCalled();
    expect((field as HTMLInputElement).value).toBe("Unsaved repair service");
  });

  it("reloads the currently selected intake after an uncertain write", async () => {
    const secondCycle = { ...cycle, id: "88888888-8888-4888-8888-888888888888", code: "2026-B", name_en: "Second intake" };
    const requests: string[] = [];
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input); requests.push(url);
      if (url.startsWith("/api/applications/mine")) return response({ items: [], next_cursor: null });
      if (url.endsWith("/cycles")) return response({ items: [cycle, secondCycle] });
      return response({ ...draft, cycle_id: url.includes(secondCycle.id) ? secondCycle.id : cycle.id });
    }));
    render(<ApplicationWorkspace locale="en" org={form.organization_id} />);
    await screen.findByLabelText("Business idea *");
    fireEvent.click(screen.getByRole("button", { name: /Second intake/ }));
    await waitFor(() => expect(screen.getByRole("button", { name: /Second intake/ }).getAttribute("disabled")).toBeNull());
    fireEvent.click(screen.getByRole("button", { name: "Reload application" }));
    await waitFor(() => expect(requests.filter((url) => url.endsWith(`/cycles/${secondCycle.id}/application`))).toHaveLength(2));
    expect(requests.filter((url) => url.endsWith(`/cycles/${cycle.id}/application`))).toHaveLength(1);
  });

  it("protects dirty answers from global client navigation", async () => {
    mockWorkspace({ open: true });
    vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<><Link href="/en/account">Global account</Link><ApplicationWorkspace locale="en" org={form.organization_id} /></>);
    fireEvent.change(await screen.findByLabelText("Business idea *"), { target: { value: "Unsaved repair service" } });
    const click = new MouseEvent("click", { bubbles: true, cancelable: true });
    fireEvent(screen.getByRole("link", { name: "Global account" }), click);
    expect(click.defaultPrevented).toBe(true);
    expect(window.confirm).toHaveBeenCalledOnce();
  });
});
