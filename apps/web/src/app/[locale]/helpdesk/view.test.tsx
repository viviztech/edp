import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { components } from "../../../lib/api-contracts";
import HelpdeskWorkspace from "./view";
import { textAttachments, words, type Ticket } from "./content";

const org = "11111111-1111-4111-8111-111111111111";
const id = "22222222-2222-4222-8222-222222222222";
const user = "33333333-3333-4333-8333-333333333333";
const secondId = "44444444-4444-4444-8444-444444444444";
const time = "2026-10-21T08:00:00Z";
const owner: Ticket = { id, number: "HD-100001", category: "technology", subject: "Synthetic support request", priority: "normal", status: "open", version: 1, created_at: time, updated_at: time, access: "owner" };
const staffTicket: Ticket = { ...owner, access: "staff", assignee_user_id: user, owner_participant_id: org, owner_user_id: org, status: "assigned" };
const response = (value: object, status = 200) => Promise.resolve(new Response(JSON.stringify(value), { status }));
type Message = components["schemas"]["MessageView"];
function mockApi(options: { ticket?: Ticket; empty?: boolean; stale?: boolean; lostCreate?: boolean; failedConversation?: boolean; claim?: boolean; claimAfterAssigned?: boolean; second?: boolean; pagination?: boolean } = {}) {
  let ticket = options.ticket ?? owner; let preference = { enabled: true, version: 1 }; let reads = 0;
  let messages: Message[] = [{ id: "message-one", body: "Initial support details", internal: false, author_user_id: org, created_at: time, attachments: [] }];
  const writes: { path: string; body: Record<string, unknown> }[] = []; const gets: string[] = [];
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input); const [path, query] = url.split("?");
    if (url === "/api/session/csrf") return response({ csrf_token: "csrf" });
    if (!init?.method) {
      gets.push(url);
      if (path.endsWith("/tickets")) return response({ items: options.empty ? [] : ((options.claim && !writes.length) || (options.claimAfterAssigned && query?.includes("queue=unassigned"))) ? [{ id: options.claimAfterAssigned ? secondId : id, number: options.claimAfterAssigned ? "HD-100002" : owner.number, category: "technology", status: "open", priority: "normal", version: 1, created_at: time, updated_at: time, access: "claim" }] : options.second ? [ticket, { ...owner, id: secondId, number: "HD-100002", subject: "Another support request" }] : [ticket], next_cursor: null });
      if (/\/tickets\/[0-9a-f-]{36}$/.test(path)) return response(options.second && path.endsWith(secondId) ? { ...owner, id: secondId, number: "HD-100002", subject: "Another support request" } : ticket);
      if (path.endsWith("/messages")) {
        reads += 1; if (options.failedConversation && writes.length && reads === 2) return response({}, 503);
        if (query?.includes("cursor=")) return response({ items: [{ ...messages[0], id: "message-two", body: "Older conversation page" }], next_cursor: null });
        return response({ items: messages, next_cursor: options.pagination ? id : null });
      }
      if (path.endsWith("/history")) return response({ items: [{ id: query?.includes("cursor=") ? "older-history" : "history", event: "created", status: "open", priority: "normal", version: 1, reason: query?.includes("cursor=") ? "Older history page" : null, actor_user_id: org, created_at: time }], next_cursor: options.pagination && !query?.includes("cursor=") ? id : null });
      if (path.endsWith("/assignees")) return response({ items: [{ id: user, display_name: "Support executive" }], next_cursor: null });
      if (path.endsWith("/notices")) return response({ items: [{ id, ticket_id: id, event: "shared_reply", ticket_version: 2, version: 1, read_at: null, created_at: time }], next_cursor: null });
      if (path.endsWith("/preference")) return response(preference);
      if (path.endsWith("/files")) return response({ collection_enabled:false, max_upload_bytes:10485760, policy:null, items:[], next_cursor:null });
    }
    const body = JSON.parse(String(init?.body)) as Record<string, unknown>; writes.push({ path, body });
    expect(new Headers(init?.headers).get("x-csrf-token")).toBe("csrf");
    if (path.endsWith("/tickets")) { if (options.lostCreate && writes.length === 1) return Promise.reject(new Error("response lost after commit")); return response(ticket, 201); }
    if (path.endsWith("/preference")) { preference = { enabled: Boolean(body.enabled), version: preference.version + 1 }; return response(preference); }
    if (path.endsWith("/read")) return response({ id, ticket_id: id, event: "shared_reply", ticket_version: 2, version: 2, read_at: time, created_at: time });
    if (options.stale && writes.length === 1) { ticket = { ...ticket, version: 2 }; return response({}, 409); }
    if (path.endsWith("/assignment")) ticket = { ...staffTicket, id: path.includes(secondId) ? secondId : id, subject: path.includes(secondId) ? "Claimed support request" : owner.subject, version: ticket.version + 1 };
    else if (path.endsWith("/messages")) { messages = [...messages, { id: `reply-${writes.length}`, body: String(body.body), internal: Boolean(body.internal), author_user_id: user, created_at: time, attachments: [] }]; ticket = { ...ticket, version: ticket.version + 1 }; }
    else if (path.endsWith("/status")) ticket = { ...ticket, status: body.status as Ticket["status"], version: ticket.version + 1 };
    else if (path.endsWith("/reopen")) ticket = { ...ticket, status: "open", version: ticket.version + 1 };
    else if (path.endsWith("/priority")) ticket = { ...ticket, priority: body.priority as Ticket["priority"], version: ticket.version + 1 };
    else throw new Error(`Unexpected ${url}`);
    return response(ticket);
  });
  vi.stubGlobal("fetch", fetchMock); return { writes, gets, fetchMock };
}
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });
const renderOwner = () => render(<HelpdeskWorkspace org={org} locale="en" userId={user} />);
async function openTicket() { fireEvent.click(await screen.findByRole("button", { name: `${owner.number}: ${owner.subject}` })); return screen.findByRole("region", { name: "Ticket details" }); }
describe("participant helpdesk", () => {
  it("retries an uncertain ticket creation with exactly the same client request ID and frozen input", async () => {
    const api = mockApi({ empty: true, lostCreate: true }); renderOwner();
    const create = screen.getByRole("region", { name: "Create ticket" });
    fireEvent.change(within(create).getByLabelText("Subject"), { target: { value: owner.subject } });
    fireEvent.change(within(create).getByLabelText("Description"), { target: { value: "Please help with registration" } });
    fireEvent.click(within(create).getByRole("button", { name: "Create ticket" }));
    const retry = await within(create).findByRole("button", { name: "Retry same ticket request" });
    expect(within(create).getByLabelText("Subject").matches(":disabled")).toBe(true);
    expect(api.writes).toHaveLength(1); fireEvent.click(retry);
    await screen.findByRole("region", { name: "Ticket details" });
    expect(api.writes).toHaveLength(2); expect(api.writes[1].body).toEqual(api.writes[0].body);
    expect(api.writes[0].body.request_id).toMatch(/^[0-9a-f-]{36}$/); expect(api.writes[0].body).not.toHaveProperty("owner_participant_id");
  });
  it("pauses stale replies, preserves drafts through refresh and submits only explicitly with latest version", async () => {
    const api = mockApi({ stale: true }); renderOwner(); const detail = await openTicket(); const reply = within(detail).getByRole("form", { name: "Reply" });
    fireEvent.change(within(reply).getByLabelText("Reply"), { target: { value: "Preserve my unsent response" } });
    fireEvent.click(within(reply).getByRole("button", { name: "Send reply" }));
    await screen.findByText(words.en.conflict); expect((within(reply).getByRole("button", { name: "Send reply" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(within(detail).getByRole("button", { name: "Refresh ticket" })); await screen.findByText(words.en.refreshed);
    expect((within(reply).getByLabelText("Reply") as HTMLTextAreaElement).value).toBe("Preserve my unsent response"); expect(api.writes).toHaveLength(1);
    fireEvent.click(within(reply).getByRole("button", { name: "Send reply" })); await waitFor(() => expect(api.writes).toHaveLength(2));
    expect(api.writes[1].body.expected_version).toBe(2); expect(api.writes[1].body.body).toBe("Preserve my unsent response");
  });
  it("distinguishes a confirmed reply from a subsequent conversation load failure", async () => {
    const api = mockApi({ failedConversation: true }); renderOwner(); const detail = await openTicket();
    const reply = within(detail).getByRole("form", { name: "Reply" }); fireEvent.change(within(reply).getByLabelText("Reply"), { target: { value: "Committed reply" } });
    fireEvent.click(within(reply).getByRole("button", { name: "Send reply" })); await screen.findByText("Saved. Refresh ticket");
    expect(api.writes).toHaveLength(1); expect((within(reply).getByLabelText("Reply") as HTMLTextAreaElement).value).toBe("");
    expect((within(reply).getByRole("button", { name: "Send reply" }) as HTMLButtonElement).disabled).toBe(true);
  });
  it("shows owner-safe controls, closes resolved tickets and reopens with an explicit reason", async () => {
    const api = mockApi({ ticket: { ...owner, status: "resolved" } }); renderOwner(); const detail = await openTicket();
    expect(within(detail).queryByLabelText("Internal note")).toBeNull(); expect(within(detail).queryByRole("form", { name: "Assign ticket" })).toBeNull();
    fireEvent.change(within(detail).getByLabelText("Status reason"), { target: { value: "The problem is fixed" } });
    fireEvent.click(within(detail).getByRole("button", { name: "Close ticket" })); await waitFor(() => expect(api.writes).toHaveLength(1));
    await waitFor(() => expect(within(detail).queryByRole("button", { name: "Close ticket" })).toBeNull());
    fireEvent.change(within(detail).getByLabelText("Reopen reason"), { target: { value: "The problem returned" } });
    fireEvent.click(within(detail).getByRole("button", { name: "Reopen ticket" })); await waitFor(() => expect(api.writes).toHaveLength(2));
    expect(api.writes.map((write) => write.body.expected_version)).toEqual([1, 2]); expect(api.writes[1].body.reason).toBe("The problem returned");
  });
  it("uses recipient notice versions for read and preference updates", async () => {
    const api = mockApi(); renderOwner(); const notices = screen.getByRole("region", { name: "My notices" });
    const preference = await within(notices).findByLabelText("Receive in-app notices"); fireEvent.click(preference);
    fireEvent.click(within(notices).getByRole("button", { name: "Save preference" })); await waitFor(() => expect(api.writes).toHaveLength(1));
    expect(api.writes[0].body).toEqual({ expected_version: 1, enabled: false });
    await waitFor(() => expect((within(notices).getByRole("button", { name: "Mark read" }) as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(within(notices).getByRole("button", { name: "Mark read" })); await within(notices).findByText("Read");
    expect(api.writes[1].body).toEqual({ expected_version: 1 }); expect(within(notices).queryByText(owner.subject)).toBeNull();
  });
  it("paginates conversation and history independently with bounded cursor requests", async () => {
    const api = mockApi({ pagination: true }); renderOwner(); const detail = await openTicket();
    const conversation = within(detail).getByRole("region", { name: "Conversation" }); fireEvent.click(within(conversation).getByRole("button", { name: "Load more" }));
    await within(conversation).findByText("Older conversation page"); expect(within(conversation).getByText("Initial support details")).toBeTruthy();
    const history = within(detail).getByRole("region", { name: "Ticket history" }); fireEvent.click(within(history).getByRole("button", { name: "Load more" }));
    await within(history).findByText("Older history page"); expect(api.gets.some((url) => url.endsWith(`/history?limit=25&cursor=${id}`))).toBe(true);
  });
  it("renders Tamil ticket, filter and notification controls", async () => {
    mockApi({ empty: true }); render(<HelpdeskWorkspace org={org} locale="ta" userId={user} />);
    expect(await screen.findByText(words.ta.empty)).toBeTruthy(); expect(screen.getByLabelText(words.ta.subject)).toBeTruthy();
    expect(screen.getByRole("region", { name: words.ta.notices })).toBeTruthy();
  });
  it("prevents a pending attachment read from moving its files into another ticket", async () => {
    const api = mockApi({ second: true }); renderOwner(); const detail = await openTicket();
    let finishRead: (value: ArrayBuffer) => void = () => { throw new Error("read not started"); };
    const bytes = new Promise<ArrayBuffer>((resolve) => { finishRead = resolve; });
    const file = Object.assign(new File(["draft attachment"], "draft.txt"), { arrayBuffer: () => bytes });
    const reply = within(detail).getByRole("form", { name: "Reply" }); fireEvent.change(within(reply).getByLabelText("Text attachments"), { target: { files: [file] } });
    const other = screen.getByRole("button", { name: "HD-100002: Another support request" }); expect((other as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(other); expect(api.gets.some((url) => url.includes(`/tickets/${secondId}`))).toBe(false);
    await act(async () => { finishRead(new TextEncoder().encode("draft attachment").buffer); });
    await within(reply).findByText("Selected files: draft.txt"); vi.spyOn(window, "confirm").mockReturnValue(true); fireEvent.click(other);
    await within(detail).findByRole("heading", { name: "Another support request" }); expect(within(detail).queryByText("Selected files: draft.txt")).toBeNull();
  });
});
describe("staff helpdesk", () => {
  it("confirms before claiming another ticket and clears the prior draft only after the claim is confirmed", async () => {
    const api = mockApi({ ticket: staffTicket, claimAfterAssigned: true }); render(<HelpdeskWorkspace org={org} locale="en" userId={user} staff permissions={["ticket.view", "ticket.update", "ticket.assign"]} />);
    const detail = await openTicket(); fireEvent.change(within(detail).getByRole("textbox", { name: "Reply" }), { target: { value: "Draft for the first ticket only" } });
    const filters = screen.getByRole("form", { name: "Ticket filters" }); fireEvent.change(within(filters).getByLabelText("Queue"), { target: { value: "unassigned" } }); fireEvent.click(within(filters).getByRole("button", { name: "Apply filters" }));
    const claim = await screen.findByRole("button", { name: "Claim ticket: HD-100002" }); const queue = screen.getByRole("region", { name: "Helpdesk queue" });
    fireEvent.change(within(queue).getByLabelText("Assignment reason"), { target: { value: "Taking the next support request" } });
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false); fireEvent.click(claim);
    expect(api.writes).toHaveLength(0); expect((within(detail).getByRole("textbox", { name: "Reply" }) as HTMLTextAreaElement).value).toBe("Draft for the first ticket only");
    confirm.mockReturnValue(true); fireEvent.click(claim); await within(detail).findByRole("heading", { name: "Claimed support request" });
    expect(api.writes).toHaveLength(1); expect((within(detail).getByRole("textbox", { name: "Reply" }) as HTMLTextAreaElement).value).toBe("");
  });
  it("keeps unassigned queue projections private and claims a ticket before loading its detail", async () => {
    const api = mockApi({ claim: true }); render(<HelpdeskWorkspace org={org} locale="en" userId={user} staff permissions={["ticket.view", "ticket.update", "ticket.assign"]} />);
    const claim = await screen.findByRole("button", { name: `Claim ticket: ${owner.number}` });
    expect(screen.queryByText(owner.subject)).toBeNull(); expect(api.gets.some((url) => url.includes(`/tickets/${id}`))).toBe(false);
    fireEvent.change(screen.getByLabelText("Assignment reason"), { target: { value: "Taking ownership for support" } }); fireEvent.click(claim);
    await screen.findByRole("region", { name: "Ticket details" }); expect(api.writes[0].body).toEqual({ expected_version: 1, assignee_user_id: user, reason: "Taking ownership for support" });
  });
  it("records staff-only notes and urgent priority using exact ticket versions", async () => {
    const api = mockApi({ ticket: staffTicket }); render(<HelpdeskWorkspace org={org} locale="en" userId={user} staff permissions={["ticket.view", "ticket.update", "ticket.assign"]} />);
    const detail = await openTicket(); const reply = within(detail).getByRole("form", { name: "Reply" });
    fireEvent.change(within(reply).getByLabelText("Reply"), { target: { value: "Private triage note" } }); fireEvent.click(within(reply).getByLabelText("Internal note"));
    fireEvent.click(within(reply).getByRole("button", { name: "Save internal note" })); await within(detail).findByText("Staff only");
    expect(api.writes[0].body.internal).toBe(true);
    const priority = within(detail).getByRole("form", { name: "Update priority" });
    fireEvent.change(within(priority).getByLabelText("Priority"), { target: { value: "urgent" } }); fireEvent.change(within(priority).getByLabelText("Priority reason"), { target: { value: "Service unavailable during enrollment" } });
    fireEvent.click(within(priority).getByRole("button", { name: "Update priority" })); await waitFor(() => expect(api.writes).toHaveLength(2));
    expect(api.writes[1].body.expected_version).toBe(2); expect(api.writes[1].body.priority).toBe("urgent");
  });
});
describe("plain-text attachment intake", () => {
  const file = (name: string, content: string) => Object.assign(new File([content], name), { arrayBuffer: async () => new TextEncoder().encode(content).buffer });
  it("preserves valid bilingual UTF-8 while rejecting misleading names, active markup, controls and oversized files", async () => {
    expect(await textAttachments([file("receipt.txt", "தமிழ் support details")])).toEqual([{ filename: "receipt.txt", content: "தமிழ் support details" }]);
    for (const item of [file("receipt.html.txt", "hello"), file("script.txt", "<script>alert(1)</script>"), file("control.txt", "bad\u0080text"), file("large.txt", "அ".repeat(12000)), file("empty.txt", "")]) await expect(textAttachments([item])).rejects.toThrow();
    await expect(textAttachments([file("a.txt", "a"), file("b.txt", "b"), file("c.txt", "c"), file("d.txt", "d")])).rejects.toThrow();
  });
});
