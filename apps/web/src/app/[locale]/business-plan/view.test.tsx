import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import type { components } from "../../../lib/api-contracts";
import { normalized, type Plan } from "./editor-state";
import BusinessPlanView, { sections } from "./view";

type Save = components["schemas"]["SaveSection"];
const org = "11111111-1111-4111-8111-111111111111";
const enrollment = "22222222-2222-4222-8222-222222222222";
const root = `/api/business-plans/organizations/${org}`;
const timestamp = "2026-10-21T08:00:00Z";

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}
function fixture(values: Record<string, string> = {}): Plan {
  return { id: "plan-1", enrollment_id: enrollment, status: "draft", version: 1,
    completed_sections: Object.values(values).filter(Boolean).length, total_sections: sections.length,
    sections: values, revisions: [], submissions: [] };
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

function mockApi(initial: Plan | null = fixture()) {
  const api = {
    saved: initial,
    reads: 0,
    writes: [] as Save[],
    submits: [] as components["schemas"]["SubmitPlan"][],
    creates: 0,
    readOverride: null as null | (() => Promise<Response>),
    saveOverride: null as null | ((body: Save) => Promise<Response>),
    submitOverride: null as null | (() => Promise<Response>),
    createOverride: null as null | (() => Promise<Response>),
    mine() { return json({ entries: [{ enrollment_id: enrollment, program_id: "program-1", plan: this.saved }] }); },
    commit(body: Save) {
      if (!this.saved || body.expected_version !== this.saved.version || !["draft", "changes_requested"].includes(this.saved.status)) return json({}, 409);
      const values = { ...this.saved.sections, [body.section_code]: normalized(body.body) };
      const version = this.saved.version + 1;
      this.saved = { ...this.saved, version, sections: values,
        completed_sections: Object.values(values).filter(Boolean).length,
        revisions: [...this.saved.revisions, { id: `revision-${version}`, version,
          section_code: body.section_code, body: normalized(body.body), created_at: timestamp }] };
      return json(this.saved);
    },
    remote(values: Record<string, string>, status: Plan["status"] = "draft") {
      this.saved = { ...this.saved!, version: this.saved!.version + 1, status,
        sections: { ...this.saved!.sections, ...values } };
    },
  };
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/session/csrf") return json({ csrf_token: "test-csrf" });
    if (url === `${root}/mine`) {
      api.reads += 1;
      return api.readOverride ? api.readOverride() : api.mine();
    }
    expect(init?.method).toBe("POST");
    expect(new Headers(init?.headers).get("x-csrf-token")).toBe("test-csrf");
    if (url.endsWith("/sections")) {
      const body = JSON.parse(String(init?.body)) as Save;
      api.writes.push(body);
      return api.saveOverride ? api.saveOverride(body) : api.commit(body);
    }
    if (url.endsWith("/submit")) {
      api.submits.push(JSON.parse(String(init?.body)) as components["schemas"]["SubmitPlan"]);
      if (api.submitOverride) return api.submitOverride();
      api.saved = { ...api.saved!, status: "submitted", version: api.saved!.version + 1 };
      return json(api.saved);
    }
    if (url.endsWith(`/enrollments/${enrollment}`)) {
      api.creates += 1;
      if (api.createOverride) return api.createOverride();
      api.saved = fixture();
      return json(api.saved);
    }
    throw new Error(`Unexpected request ${url}`);
  }));
  return api;
}

async function open(locale: "en" | "ta" = "en") {
  await act(async () => { render(<BusinessPlanView org={org} locale={locale} />); });
}
function edit(label: string, value: string) { fireEvent.change(screen.getByLabelText(label), { target: { value } }); }
function value(label: string) { return (screen.getByLabelText(label) as HTMLTextAreaElement).value; }
async function tick(milliseconds = 950) { await act(async () => { await vi.advanceTimersByTimeAsync(milliseconds); }); }
async function click(name: string) { await act(async () => { fireEvent.click(screen.getByRole("button", { name })); }); }
const submit = () => screen.getByRole("button", { name: "Submit for mentor review" }) as HTMLButtonElement;

beforeEach(() => { vi.useFakeTimers(); });
afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("business-plan autosave recovery", () => {
  it("merges independent remote edits and saves every local dirty section using the refreshed version", async () => {
    const api = mockApi(fixture({ executive_summary: "Original", problem: "Original problem" }));
    await open();
    edit("Executive summary", "Local summary");
    edit("Solution", "Local solution");
    api.remote({ problem: "Remote problem" });
    await tick();
    expect(api.writes).toHaveLength(1);
    expect(value("Problem")).toBe("Remote problem");
    expect(value("Executive summary")).toBe("Local summary");
    expect(submit().disabled).toBe(true);
    await tick();
    await tick();
    expect(api.writes.map((write) => write.expected_version)).toEqual([1, 2, 3]);
    expect(api.saved?.sections).toMatchObject({ executive_summary: "Local summary", problem: "Remote problem", solution: "Local solution" });
    expect(screen.getByRole("status").textContent).toBe("Saved");
  });

  it("compares overlapping changes, pauses until an explicit keep choice, and reconciles repeated conflicts", async () => {
    const api = mockApi(fixture({ executive_summary: "Original" }));
    await open();
    edit("Executive summary", "Local draft");
    api.remote({ executive_summary: "Remote draft" });
    await tick();
    const comparison = screen.getByRole("region", { name: "Review conflicting edits" });
    expect([...comparison.querySelectorAll("pre")].map((node) => node.textContent)).toEqual(["Remote draft", "Local draft"]);
    await tick(5000);
    expect(api.writes).toHaveLength(1);
    expect(submit().disabled).toBe(true);
    await click("Keep my edits");
    api.remote({ executive_summary: "Newer remote draft" });
    await tick();
    expect(api.writes.at(-1)?.expected_version).toBe(2);
    expect(screen.getByRole("region", { name: "Review conflicting edits" }).textContent).toContain("Newer remote draft");
    await click("Keep my edits");
    await tick();
    expect(api.writes.at(-1)?.expected_version).toBe(3);
    expect(api.saved?.sections.executive_summary).toBe("Local draft");
  });

  it("requires confirmation before discarding all unsaved edits and loading the saved plan", async () => {
    const api = mockApi(fixture({ executive_summary: "Original" }));
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    await open();
    edit("Executive summary", "Local draft");
    edit("Solution", "Another local edit");
    api.remote({ executive_summary: "Remote draft" });
    await tick();
    await click("Load saved version");
    expect(confirm).toHaveBeenCalledWith("Discard all unsaved edits and load the saved version?");
    expect(value("Executive summary")).toBe("Local draft");
    expect(value("Solution")).toBe("Another local edit");
    confirm.mockReturnValue(true);
    await click("Load saved version");
    expect(value("Executive summary")).toBe("Remote draft");
    expect(value("Solution")).toBe("");
    await tick(3000);
    expect(api.writes).toHaveLength(1);
  });

  it("recognizes a committed write after a lost response without creating a duplicate revision", async () => {
    const api = mockApi();
    api.saveOverride = async (body) => { api.commit(body); throw new Error("response_lost"); };
    await open();
    edit("Executive summary", "Saved despite response loss");
    await tick(5000);
    expect(api.reads).toBe(2);
    expect(api.writes).toHaveLength(1);
    expect(api.saved?.revisions).toHaveLength(1);
    expect(value("Executive summary")).toBe("Saved despite response loss");
  });

  it("does not write when remote and local edits are already equivalent after API whitespace normalization", async () => {
    const api = mockApi();
    await open();
    edit("Executive summary", "  Same text\n");
    api.remote({ executive_summary: "Same text" });
    await tick(5000);
    expect(api.writes).toHaveLength(1);
    expect(screen.queryByRole("button", { name: "Keep my edits" })).toBeNull();
    expect(value("Executive summary")).toBe("Same text");
  });

  it("preserves newer typing during a successful normalized save and adopts independent changes in its response", async () => {
    const api = mockApi(fixture({ problem: "Original problem" }));
    const pending = deferred<Response>();
    api.saveOverride = () => pending.promise;
    await open();
    edit("Executive summary", "  First text  ");
    await tick();
    edit("Executive summary", "Newer typing");
    const request = api.writes[0];
    api.commit(request);
    api.remote({ problem: "Remote after commit" });
    api.saveOverride = null;
    await act(async () => { pending.resolve(json(api.saved)); });
    expect(value("Executive summary")).toBe("Newer typing");
    expect(value("Problem")).toBe("Remote after commit");
    expect(screen.getByRole("status").textContent).toBe("Unsaved changes");
    await tick(4000);
    expect(api.writes).toHaveLength(2);
    expect(api.writes[1].expected_version).toBe(3);
    expect(api.saved?.sections.executive_summary).toBe("Newer typing");
  });

  it("acknowledges normalized successful text without repeated revisions", async () => {
    const api = mockApi();
    await open();
    edit("Executive summary", "\u0085  Normalized text\n");
    await tick(5000);
    expect(api.writes).toHaveLength(1);
    expect(value("Executive summary")).toBe("Normalized text");
  });

  it.each(["success", "lost response"])("retains a revert typed while a %s is pending", async (mode) => {
    const api = mockApi();
    const pending = deferred<Response>();
    api.saveOverride = () => pending.promise;
    await open();
    edit("Executive summary", "Pending text");
    await tick();
    edit("Executive summary", "");
    const unloading = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(unloading);
    expect(unloading.defaultPrevented).toBe(true);
    api.commit(api.writes[0]);
    api.saveOverride = null;
    await act(async () => {
      if (mode === "success") pending.resolve(json(api.saved));
      else pending.reject(new Error("response_lost"));
    });
    expect(value("Executive summary")).toBe("");
    if (mode === "lost response") await click("Refresh saved plan");
    await tick();
    expect(api.saved?.sections.executive_summary).toBe("");
    expect(api.writes).toHaveLength(2);
  });

  it("preserves typing in every section while owner-scoped refresh is pending", async () => {
    const api = mockApi(fixture({ problem: "Old problem" }));
    const pending = deferred<Response>();
    await open();
    api.readOverride = () => pending.promise;
    edit("Executive summary", "First local text");
    api.remote({ problem: "Remote problem" });
    await tick();
    edit("Executive summary", "Newer local text");
    edit("Solution", "Typed during refresh");
    await act(async () => { pending.resolve(api.mine()); });
    expect(value("Executive summary")).toBe("Newer local text");
    expect(value("Solution")).toBe("Typed during refresh");
    expect(value("Problem")).toBe("Remote problem");
    api.readOverride = null;
    await tick();
    await tick();
    expect(api.saved?.sections).toMatchObject({ executive_summary: "Newer local text", solution: "Typed during refresh" });
  });

  it.each([false, true])("fences a reverted edit when an ambiguous save commits late, including first refresh failure: %s", async (firstRefreshFails) => {
    const api = mockApi();
    const pending = deferred<Response>();
    api.saveOverride = () => pending.promise;
    await open();
    if (firstRefreshFails) api.readOverride = async () => { throw new Error("refresh_offline"); };
    edit("Executive summary", "Late committing text");
    await tick();
    edit("Executive summary", "");
    await act(async () => { pending.reject(new Error("connection_closed_before_commit")); });
    expect(api.reads).toBe(2);
    expect(api.saved?.version).toBe(1);
    expect(value("Executive summary")).toBe("");
    expect(screen.getByRole("alert").textContent?.toLowerCase()).toContain("saving is paused");
    const leaving = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(leaving);
    expect(leaving.defaultPrevented).toBe(true);
    await tick(5000);
    expect(api.writes).toHaveLength(1);

    api.readOverride = null;
    await click("Refresh saved plan");
    // The old request wins the race after the retry refresh but before its version-checked POST.
    api.commit(api.writes[0]);
    api.saveOverride = null;
    await tick();
    expect(api.writes[1]).toMatchObject({ expected_version: 1, body: "" });
    expect(value("Executive summary")).toBe("");
    expect(screen.getByRole("region", { name: "Review conflicting edits" }).querySelector("pre")?.textContent).toBe("Late committing text");
    await click("Keep my edits");
    await tick();
    expect(api.writes[2]).toMatchObject({ expected_version: 2, body: "" });
    expect(api.saved?.sections.executive_summary).toBe("");
    expect(screen.getByRole("status").textContent).toBe("Saved");
    const savedLeaving = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(savedLeaving);
    expect(savedLeaving.defaultPrevented).toBe(false);
  });

  it.each(["submitted", "approved"] as const)("keeps local text and stops writing when refresh discovers a %s plan", async (status) => {
    const api = mockApi();
    await open();
    edit("Executive summary", "Preserved local text");
    api.remote({}, status);
    await tick(5000);
    expect(value("Executive summary")).toBe("Preserved local text");
    expect((screen.getByLabelText("Executive summary") as HTMLTextAreaElement).readOnly).toBe(true);
    expect(screen.getByRole("alert").textContent).toContain("cannot be saved");
    expect(screen.getByRole("status").textContent).toBe("");
    expect(screen.queryByRole("button", { name: "Keep my edits" })).toBeNull();
    expect(api.writes).toHaveLength(1);
  });

  it("keeps uncertain write intent when the user reverts after an early refresh, then recognizes the late commit", async () => {
    const api = mockApi();
    const pending = deferred<Response>();
    api.saveOverride = () => pending.promise;
    await open();
    edit("Executive summary", "Attempted text");
    await tick();
    edit("Executive summary", "Newer local typing");
    await act(async () => { pending.reject(new Error("early_connection_failure")); });
    expect(api.saved?.version).toBe(1);
    edit("Executive summary", "");
    const leaving = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(leaving);
    expect(leaving.defaultPrevented).toBe(true);
    api.commit(api.writes[0]);
    api.saveOverride = null;
    await click("Refresh saved plan");
    expect(value("Executive summary")).toBe("");
    await tick();
    expect(api.saved?.sections.executive_summary).toBe("");
    expect(api.writes).toHaveLength(2);
    expect(api.writes[1].expected_version).toBe(2);
  });

  it.each([false, true])("preserves uncertain section intent when another section retries first, including a later revert: %s", async (revert) => {
    const api = mockApi(fixture({ milestones: "Original milestone" }));
    const first = deferred<Response>();
    const second = deferred<Response>();
    api.saveOverride = () => first.promise;
    await open();
    edit("Milestones", "Uncertain milestone");
    await tick();
    await act(async () => { first.reject(new Error("first_connection_lost")); });
    edit("Executive summary", "Another local section");
    await click("Refresh saved plan");
    api.saveOverride = () => second.promise;
    await tick();
    expect(api.writes[1].section_code).toBe("executive_summary");
    if (revert) edit("Milestones", "Original milestone");
    api.commit(api.writes[0]);
    api.saveOverride = null;
    await act(async () => { second.resolve(json({}, 409)); });
    expect(value("Milestones")).toBe(revert ? "Original milestone" : "Uncertain milestone");
    if (revert) {
      expect(screen.getByRole("region", { name: "Review conflicting edits" }).textContent).toContain("Uncertain milestone");
      await click("Keep my edits");
    }
    await tick();
    if (revert) await tick();
    expect(api.saved?.sections).toMatchObject({ executive_summary: "Another local section",
      milestones: revert ? "Original milestone" : "Uncertain milestone" });
    expect(api.writes.filter((write) => write.section_code === "milestones")).toHaveLength(revert ? 2 : 1);
    expect(screen.getByRole("status").textContent).toBe("Saved");
  });

  it.each(["network", "403", "missing enrollment", "missing plan"])("keeps drafts paused after refresh failure: %s", async (failure) => {
    const api = mockApi();
    await open();
    api.readOverride = async () => {
      if (failure === "network") throw new Error("offline");
      if (failure === "403") return json({}, 403);
      if (failure === "missing enrollment") return json({ entries: [] });
      return json({ entries: [{ enrollment_id: enrollment, program_id: "program-1", plan: null }] });
    };
    edit("Executive summary", "Preserve me");
    api.remote({ problem: "Remote problem" });
    await tick(5000);
    expect(value("Executive summary")).toBe("Preserve me");
    expect(screen.getByRole("alert").textContent).toContain("confirm your access");
    expect(api.writes).toHaveLength(1);
    expect(submit().disabled).toBe(true);
    api.readOverride = null;
    await click("Refresh saved plan");
    expect(api.writes).toHaveLength(1);
    await tick();
    expect(api.saved?.sections.executive_summary).toBe("Preserve me");
    expect(api.writes[1].expected_version).toBe(2);
  });

  it.each([413, 422, 429, 503])("does not repeatedly replay a rejected %s save and refreshes before manual retry", async (status) => {
    const api = mockApi();
    api.saveOverride = async () => json({}, status);
    await open();
    edit("Executive summary", "Rejected text");
    await tick(10000);
    expect(api.writes).toHaveLength(1);
    expect(api.reads).toBe(2);
    expect(screen.getByRole("alert").textContent).toContain("saving is paused");
    expect(value("Executive summary")).toBe("Rejected text");
    edit("Executive summary", "Corrected text");
    await tick(3000);
    expect(api.writes).toHaveLength(1);
    api.saveOverride = null;
    await click("Refresh saved plan");
    expect(api.reads).toBe(3);
    expect(api.writes).toHaveLength(1);
    await tick();
    expect(api.saved?.sections.executive_summary).toBe("Corrected text");
  });

  it("refreshes after an uncommitted ambiguous failure and waits for a manual retry", async () => {
    const api = mockApi();
    api.saveOverride = async () => { throw new Error("offline"); };
    await open();
    edit("Executive summary", "Offline text");
    await tick(10000);
    expect(api.writes).toHaveLength(1);
    api.saveOverride = null;
    await click("Refresh saved plan");
    await tick();
    expect(api.saved?.sections.executive_summary).toBe("Offline text");
  });

  it("blocks submission while dirty and makes fields read-only during submission, recovering a lost submit response", async () => {
    const values = Object.fromEntries(sections.map(([code]) => [code, `Content for ${code}`]));
    const api = mockApi(fixture(values));
    const pending = deferred<Response>();
    await open();
    expect(submit().disabled).toBe(false);
    edit("Executive summary", "Updated summary");
    expect(submit().disabled).toBe(true);
    await tick();
    api.submitOverride = () => pending.promise;
    await click("Submit for mentor review");
    expect((screen.getByLabelText("Executive summary") as HTMLTextAreaElement).readOnly).toBe(true);
    api.saved = { ...api.saved!, status: "submitted", version: api.saved!.version + 1 };
    await act(async () => { pending.reject(new Error("response_lost")); });
    expect(screen.getByText("Submitted for review")).toBeTruthy();
    await tick(3000);
    expect(api.submits).toHaveLength(1);
    expect(api.reads).toBe(2);
    expect(screen.queryByRole("button", { name: "Submit for mentor review" })).toBeNull();
  });

  it("refreshes an ambiguous create response and uses the already created plan", async () => {
    const api = mockApi(null);
    api.createOverride = async () => { api.saved = fixture(); throw new Error("response_lost"); };
    await open();
    await click("Start a plan");
    expect(screen.getByLabelText("Executive summary")).toBeTruthy();
    expect(api.creates).toBe(1);
    expect(api.reads).toBe(2);
  });

  it("refreshes a stale submission without resubmitting automatically or losing the latest saved sections", async () => {
    const values = Object.fromEntries(sections.map(([code]) => [code, `Content for ${code}`]));
    const api = mockApi(fixture(values));
    api.submitOverride = async () => json({}, 409);
    await open();
    api.remote({ problem: "Updated elsewhere before submission" });
    await click("Submit for mentor review");
    expect(value("Problem")).toBe("Updated elsewhere before submission");
    await tick(5000);
    expect(api.submits).toHaveLength(1);
    expect(api.writes).toHaveLength(0);
    expect(submit().disabled).toBe(false);
    api.submitOverride = null;
    await click("Submit for mentor review");
    expect(api.submits.at(-1)?.expected_version).toBe(2);
    expect(screen.getByText("Submitted for review")).toBeTruthy();
  });

  it("warns on ordinary link navigation and tab close until edits are saved", async () => {
    mockApi();
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    await open();
    const link = document.createElement("a");
    link.href = "/en/account";
    link.textContent = "Your account";
    document.body.appendChild(link);
    edit("Executive summary", "Unsaved text");
    expect(fireEvent.click(link)).toBe(false);
    expect(confirm).toHaveBeenCalledOnce();
    const before = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(before);
    expect(before.defaultPrevented).toBe(true);
    await tick();
    const after = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(after);
    expect(after.defaultPrevented).toBe(false);
    link.remove();
  });

  it("renders Tamil conflict recovery and comparison controls", async () => {
    const api = mockApi();
    await open("ta");
    const summary = sections[0][2];
    edit(summary, "என் திருத்தம்");
    api.remote({ executive_summary: "சேமித்த திருத்தம்" });
    await tick();
    const comparison = screen.getByRole("region", { name: "முரண்படும் திருத்தங்களைப் பரிசீலிக்கவும்" });
    expect(within(comparison).getByText("சேமித்த பதிப்பு")).toBeTruthy();
    expect(within(comparison).getByText("உங்கள் திருத்தங்கள்")).toBeTruthy();
    expect(screen.getByRole("button", { name: "என் திருத்தங்களை வைத்திரு" })).toBeTruthy();
  });

  it.each([
    ["en", "changes_requested", "Changes requested"],
    ["en", "approved", "Approved"],
    ["ta", "changes_requested", "மாற்றங்கள் கோரப்பட்டன"],
    ["ta", "approved", "ஒப்புதல் அளிக்கப்பட்டது"],
  ] as const)("localizes recorded %s feedback for %s", async (locale, decision, expected) => {
    const plan = fixture({ problem: "Submitted evidence" });
    plan.status = decision;
    plan.submissions = [{ id: "submission-1", enrollment_id: enrollment, plan_version: 3, number: 1,
      snapshot: { problem: "Submitted evidence" }, created_at: timestamp,
      review: { id: "review-1", decision, reason: "Review reason", comments: { problem: "Section feedback" }, created_at: timestamp } }];
    mockApi(plan);
    await open(locale);
    expect(screen.getByRole("heading", { level: 3 }).textContent).toContain(expected);
    expect(screen.getByText("Section feedback", { exact: false })).toBeTruthy();
    expect(screen.queryByText(decision, { exact: true })).toBeNull();
  });
});
