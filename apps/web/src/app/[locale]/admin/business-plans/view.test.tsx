import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { components } from "../../../../lib/api-contracts";
import MentorPlanReviews from "./view";

type Submission = components["schemas"]["SubmissionView"];
type Command = components["schemas"]["ReviewPlan"];
const org = "11111111-1111-4111-8111-111111111111";
const enrollment = "22222222-2222-4222-8222-222222222222";
const root = `/api/business-plans/organizations/${org}`;
const timestamp = "2026-10-21T08:00:00Z";
const errorText = "Could not load or save the review. Your entered feedback is still here.";

function submission(overrides: Partial<Submission> = {}): Submission {
  return { id: "submission-1", enrollment_id: enrollment, number: 1, plan_version: 22,
    snapshot: { executive_summary: "Immutable submitted summary", problem: "Submitted problem" },
    created_at: timestamp, review: null, ...overrides };
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function mockApi(initial = [submission()]) {
  const api = {
    items: structuredClone(initial), writes: [] as Command[], reads: 0,
    readStatus: 200, postStatus: 200, csrfStatus: 200, loseResponse: false,
    failRefreshAfterWrite: false, gate: null as Promise<void> | null,
  };
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/session/csrf") return json({ csrf_token: "review-csrf" }, api.csrfStatus);
    if (url.endsWith("/assigned") && !init?.method) {
      api.reads += 1;
      return json({ submissions: api.items }, api.readStatus);
    }
    if (url.startsWith(`${root}/submissions/`) && url.endsWith("/review") && init?.method === "POST") {
      expect(new Headers(init.headers).get("x-csrf-token")).toBe("review-csrf");
      const command = JSON.parse(String(init.body)) as Command;
      expect(Object.keys(command).sort()).toEqual(["comments", "decision", "expected_version", "reason"]);
      api.writes.push(command);
      if (api.gate) await api.gate;
      if (api.postStatus !== 200) return json({ error: { code: "review_failed" } }, api.postStatus);
      const id = url.slice(`${root}/submissions/`.length, -"/review".length);
      const item = api.items.find((candidate) => candidate.id === id)!;
      if (item.review || item.plan_version !== command.expected_version) return json({}, 409);
      const review = { id: `review-${id}`, decision: command.decision, reason: command.reason,
        comments: command.comments ?? {}, created_at: timestamp };
      api.items = api.items.map((candidate) => ({ ...candidate,
        plan_version: candidate.enrollment_id === item.enrollment_id ? candidate.plan_version + 1 : candidate.plan_version,
        review: candidate.id === id ? review : candidate.review,
      }));
      if (api.failRefreshAfterWrite) api.readStatus = 503;
      if (api.loseResponse) throw new TypeError("Connection interrupted");
      return json(review);
    }
    throw new Error(`Unexpected request: ${init?.method ?? "GET"} ${url}`);
  }));
  return api;
}

async function enterReview(reason = "Clarify the customer evidence") {
  fireEvent.change(await screen.findByLabelText("Review reason"), { target: { value: reason } });
  fireEvent.click(screen.getByText("Comments for this section"));
  fireEvent.change(screen.getByLabelText("Executive summary"), { target: { value: "  Add customer interviews  " } });
  fireEvent.change(screen.getByLabelText("Problem"), { target: { value: "  " } });
}

function record() { fireEvent.click(screen.getByRole("button", { name: "Record review" })); }
function refresh() { fireEvent.click(screen.getByRole("button", { name: "Refresh assigned plans" })); }
function reason() { return screen.getByLabelText("Review reason") as HTMLTextAreaElement; }

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("assigned mentor plan reviews", () => {
  it.each(["changes_requested", "approved"] as const)("records %s with the current version, CSRF and only nonblank section comments", async (decision) => {
    const api = mockApi();
    render(<MentorPlanReviews org={org} locale="en" />);
    await enterReview("  Clarify the customer evidence  ");
    fireEvent.change(screen.getByLabelText("Decision"), { target: { value: decision } });
    record();
    await screen.findByText("Review saved.");
    expect(api.writes).toEqual([{ expected_version: 22, decision,
      reason: "Clarify the customer evidence", comments: { executive_summary: "Add customer interviews" } }]);
    expect(screen.getByRole("heading", { name: `Recorded feedback: ${decision === "approved" ? "Approved" : "Changes requested"}` })).toBeDefined();
    expect(screen.queryByRole("button", { name: "Record review" })).toBeNull();
    expect(screen.getByText("Immutable submitted summary")).toBeDefined();
    expect(api.reads).toBe(2);
  });

  it("keeps entered feedback on validation failure and refreshes the version before a manual retry", async () => {
    const api = mockApi(); api.postStatus = 422;
    render(<MentorPlanReviews org={org} locale="en" />);
    await enterReview(); record();
    await screen.findByText(errorText);
    expect(reason().value).toBe("Clarify the customer evidence");
    expect((screen.getByLabelText("Executive summary") as HTMLTextAreaElement).value).toBe("  Add customer interviews  ");
    expect((screen.getByRole("button", { name: "Record review" }) as HTMLButtonElement).disabled).toBe(true);
    record(); expect(api.writes).toHaveLength(1);
    api.items[0].plan_version = 24; api.postStatus = 200;
    refresh();
    await waitFor(() => expect((screen.getByRole("button", { name: "Record review" }) as HTMLButtonElement).disabled).toBe(false));
    expect(reason().value).toBe("Clarify the customer evidence");
    record(); await screen.findByText("Review saved.");
    expect(api.writes.map((command) => command.expected_version)).toEqual([22, 24]);
  });

  it("retains a stale review draft alongside another mentor's recorded evidence without replaying it", async () => {
    const api = mockApi();
    render(<MentorPlanReviews org={org} locale="en" />);
    await enterReview();
    api.items[0] = { ...api.items[0], plan_version: 23, review: { id: "other-review", decision: "approved",
      reason: "Evidence meets the criteria", comments: {}, created_at: timestamp } };
    record();
    await screen.findByText(/This plan changed or was already reviewed/);
    expect(reason().value).toBe("Clarify the customer evidence");
    refresh();
    await screen.findByRole("heading", { name: "Recorded feedback: Approved" });
    expect(screen.getByRole("heading", { name: "Your unrecorded review" })).toBeDefined();
    expect(reason().value).toBe("Clarify the customer evidence");
    expect(reason().matches(":disabled")).toBe(true);
    expect(api.writes).toHaveLength(1);
  });

  it("reconciles a lost committed response on refresh without creating another review", async () => {
    const api = mockApi(); api.loseResponse = true;
    render(<MentorPlanReviews org={org} locale="en" />);
    await enterReview(); record();
    await screen.findByText(errorText);
    expect(reason().value).toBe("Clarify the customer evidence");
    refresh();
    await screen.findByText("Review saved.");
    expect(screen.getByRole("heading", { name: "Recorded feedback: Changes requested" })).toBeDefined();
    expect(screen.queryByRole("button", { name: "Record review" })).toBeNull();
    expect(api.writes).toHaveLength(1);
  });

  it("keeps the committed result locked when the follow-up assigned list refresh fails", async () => {
    const api = mockApi(); api.failRefreshAfterWrite = true;
    render(<MentorPlanReviews org={org} locale="en" />);
    await enterReview(); record();
    await screen.findByText("Review saved. The assigned list could not be refreshed; your recorded review is shown below.");
    expect(screen.getByRole("heading", { name: "Recorded feedback: Changes requested" })).toBeDefined();
    expect(screen.queryByRole("button", { name: "Record review" })).toBeNull();
    expect(api.writes).toHaveLength(1);
    api.readStatus = 200; refresh();
    await waitFor(() => expect(api.reads).toBe(3));
    expect(api.writes).toHaveLength(1);
  });

  it("preserves newer local feedback typed after an ambiguous save when the earlier review is confirmed", async () => {
    const api = mockApi(); api.loseResponse = true;
    render(<MentorPlanReviews org={org} locale="en" />);
    await enterReview(); record(); await screen.findByText(errorText);
    fireEvent.change(reason(), { target: { value: "Newer feedback not included in the recorded review" } });
    refresh(); await screen.findByText("Review saved.");
    expect(screen.getByRole("heading", { name: "Your unrecorded review" })).toBeDefined();
    expect(reason().value).toBe("Newer feedback not included in the recorded review");
    expect(reason().matches(":disabled")).toBe(true);
    expect(screen.getByText("Clarify the customer evidence")).toBeDefined();
    expect(api.writes).toHaveLength(1);
  });

  it("freezes all review inputs while recording the captured decision", async () => {
    const api = mockApi();
    let release!: () => void;
    api.gate = new Promise<void>((resolve) => { release = resolve; });
    render(<MentorPlanReviews org={org} locale="en" />);
    await enterReview(); record();
    await waitFor(() => expect(api.writes).toHaveLength(1));
    expect(reason().matches(":disabled")).toBe(true);
    expect(screen.getByLabelText("Decision").matches(":disabled")).toBe(true);
    expect(screen.getByLabelText("Executive summary").matches(":disabled")).toBe(true);
    record(); expect(api.writes).toHaveLength(1);
    release(); await screen.findByText("Review saved.");
  });

  it("keeps CSRF failures local and requires a refresh before retrying", async () => {
    const api = mockApi(); api.csrfStatus = 403;
    render(<MentorPlanReviews org={org} locale="en" />);
    await enterReview(); record();
    await screen.findByText(errorText);
    expect(api.writes).toHaveLength(0);
    expect(reason().value).toBe("Clarify the customer evidence");
    expect(screen.getByRole("button", { name: "Record review" }).matches(":disabled")).toBe(true);
  });

  it("selects the latest submission per enrollment independently of queue order and shows only submitted snapshots", async () => {
    mockApi([submission(), submission({ id: "submission-3", number: 3, snapshot: { executive_summary: "Latest submitted evidence" } }),
      submission({ id: "submission-2", number: 2 }),
      submission({ id: "other-enrollment", enrollment_id: "other", number: 1 })]);
    render(<MentorPlanReviews org={org} locale="en" />);
    await screen.findByText("Latest submitted evidence");
    const historical = screen.getByRole("heading", { name: "Submitted version 2" }).closest("section")!;
    expect(within(historical).queryByRole("button", { name: "Record review" })).toBeNull();
    const latest = screen.getByRole("heading", { name: "Submitted version 3" }).closest("section")!;
    expect(within(latest).getByRole("button", { name: "Record review" })).toBeDefined();
    expect(screen.getAllByRole("button", { name: "Record review" })).toHaveLength(2);
  });

  it("keeps entered comments read-only when a refreshed assignment disappears", async () => {
    const api = mockApi(); api.postStatus = 404;
    render(<MentorPlanReviews org={org} locale="en" />);
    await enterReview(); record(); await screen.findByText(errorText);
    api.items = []; refresh();
    await screen.findByRole("alert");
    expect(reason().value).toBe("Clarify the customer evidence");
    expect(reason().matches(":disabled")).toBe(true);
    expect((screen.getByLabelText("Executive summary") as HTMLTextAreaElement).value).toBe("  Add customer interviews  ");
    expect(api.writes).toHaveLength(1);
  });

  it("keeps the stale draft and stops writes when refreshing fails", async () => {
    const api = mockApi(); api.postStatus = 409;
    render(<MentorPlanReviews org={org} locale="en" />);
    await enterReview(); record(); await screen.findByText(/This plan changed or was already reviewed/);
    api.readStatus = 503; refresh(); await screen.findByText(errorText);
    expect(reason().value).toBe("Clarify the customer evidence");
    expect(screen.getByRole("button", { name: "Record review" }).matches(":disabled")).toBe(true);
    expect(api.writes).toHaveLength(1);
  });

  it("does not retarget stale comments to a participant's newer submission", async () => {
    const api = mockApi(); api.postStatus = 409;
    render(<MentorPlanReviews org={org} locale="en" />);
    await enterReview(); record(); await screen.findByText(/This plan changed or was already reviewed/);
    api.items.push(submission({ id: "submission-2", number: 2, plan_version: 24 }));
    refresh(); await screen.findByRole("heading", { name: "Submitted version 2" });
    const earlier = screen.getByRole("heading", { name: "Submitted version 1" }).closest("section")!;
    expect((within(earlier).getByLabelText("Review reason") as HTMLTextAreaElement).value).toBe("Clarify the customer evidence");
    expect(within(earlier).getByLabelText("Review reason").matches(":disabled")).toBe(true);
    const latest = screen.getByRole("heading", { name: "Submitted version 2" }).closest("section")!;
    expect((within(latest).getByLabelText("Review reason") as HTMLTextAreaElement).value).toBe("");
    expect(api.writes).toHaveLength(1);
  });

  it("allows retrying an initial list error", async () => {
    const api = mockApi(); api.readStatus = 503;
    render(<MentorPlanReviews org={org} locale="en" />);
    await screen.findByRole("alert");
    api.readStatus = 200; refresh();
    await screen.findByLabelText("Review reason");
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("rejects whitespace-only review reasons before posting", async () => {
    const api = mockApi();
    render(<MentorPlanReviews org={org} locale="en" />);
    await enterReview("   ");
    fireEvent.submit(reason().closest("form")!);
    await screen.findByText("Enter a review reason with at least 3 non-space characters.");
    expect(api.writes).toHaveLength(0);
  });

  it("uses Python whitespace normalization and retains FEFF comments when reconciling a lost response", async () => {
    const api = mockApi(); api.loseResponse = true;
    render(<MentorPlanReviews org={org} locale="en" />);
    await enterReview("\u0085  Evidence reviewed  \u0085");
    fireEvent.change(screen.getByLabelText("Executive summary"), { target: { value: "\ufeff" } });
    fireEvent.change(screen.getByLabelText("Problem"), { target: { value: "\u001c\u0085" } });
    record(); await screen.findByText(errorText);
    expect(api.writes[0]).toEqual({ expected_version: 22, decision: "changes_requested", reason: "Evidence reviewed",
      comments: { executive_summary: "\ufeff" } });
    refresh(); await screen.findByText("Review saved.");
    expect(screen.queryByRole("heading", { name: "Your unrecorded review" })).toBeNull();
    expect(api.writes).toHaveLength(1);
  });

  it("localizes immutable review decisions in Tamil", async () => {
    mockApi([submission({ review: { id: "review-1", decision: "approved", reason: "Strong evidence",
      comments: { executive_summary: "Clear summary" }, created_at: timestamp } })]);
    render(<MentorPlanReviews org={org} locale="ta" />);
    await screen.findByRole("heading", { name: "பதிவான கருத்து: ஒப்புதல் அளிக்கப்பட்டது" });
    expect(screen.queryByText(/changes_requested|approved/)).toBeNull();
    expect(screen.getByText(/Clear summary/)).toBeDefined();
  });
});
