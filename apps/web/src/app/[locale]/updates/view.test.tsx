import { StrictMode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import Updates from "./view";
import { updateMessages } from "./content";
import type { ParticipantNotice } from "./types";

const org = "11111111-1111-4111-8111-111111111111", id = "22222222-2222-4222-8222-222222222222", next = "33333333-3333-4333-8333-333333333333";
const root = `/api/participant-notifications/organizations/${org}`, mine = root + "/mine?limit=25";
const item = (extra: Partial<ParticipantNotice> = {}): ParticipantNotice => ({ id, enrollment_id: org, topic: "enrollment_created", template_version: "enrollment-created-v1", action_kind: "schedule", created_at: new Date(Date.now() - 60000).toISOString(), expires_at: new Date(Date.now() + 3600000).toISOString(), read_at: null, version: 1, ...extra });
const pref = (enabled = true, version = 0) => ({ enabled, version, topic: "enrollment_created" });
const list = (items: ParticipantNotice[] = [], cursor: string | null = null) => Response.json({ items, next_cursor: cursor });
async function settle() { await act(async () => {}); }
async function click(name: string) { await act(async () => { fireEvent.click(screen.getByRole("button", { name })); }); }
afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("participant updates", () => {
  it("loads without CRM grants, renders a fixed same-organization schedule action and marks read through explicit CSRF POST", async () => {
    const mock = vi.fn(async (url: string, init?: RequestInit) => url === mine ? list([item()])
      : url === root + "/preference" ? Response.json(pref()) : url === "/api/session/csrf" ? Response.json({ csrf_token: "csrf-endpoint" })
        : init?.method === "POST" ? Response.json(item({ read_at: new Date().toISOString(), version: 2 })) : Response.json({}, { status: 404 }));
    vi.stubGlobal("fetch", mock); render(<Updates org={org} locale="en" />); await settle();
    expect(screen.getByRole("link", { name: updateMessages.en.schedule }).getAttribute("href")).toBe(`/en/participant?organization=${org}`);
    expect(screen.getByText(updateMessages.en.unread)).toBeTruthy();
    expect(mock.mock.calls.filter(call => call[1]?.method === "POST")).toHaveLength(0);
    await click(updateMessages.en.markRead);
    expect(screen.getByText(updateMessages.en.read)).toBeTruthy(); expect(screen.queryByRole("button", { name: updateMessages.en.markRead })).toBeNull();
    expect(mock.mock.calls.find(call => call[1]?.method === "POST")).toEqual([`${root}/${id}/read`, expect.objectContaining({ body: '{"expected_version":1}', headers: { "Content-Type": "application/json", "x-csrf-token": "csrf-endpoint" } })]);
  });
  it("preserves failed pagination and its cursor, deduplicates a repeated page, and retries reads only", async () => {
    let pages = 0;
    const mock = vi.fn(async (url: string) => url === mine ? list([item()], id) : url === root + "/preference" ? Response.json(pref())
      : ++pages === 1 ? Response.json({}, { status: 503 }) : list([item(), item({ id: next })]));
    vi.stubGlobal("fetch", mock); render(<Updates org={org} locale="en" />); await settle();
    await click(updateMessages.en.more); expect(screen.getByText(updateMessages.en.error)).toBeTruthy(); expect(screen.getAllByRole("article")).toHaveLength(1);
    await click(updateMessages.en.more); expect(screen.getAllByRole("article")).toHaveLength(2);
    expect(mock.mock.calls.filter(call => call[0] === `${mine}&cursor=${id}`)).toHaveLength(2);
    expect(screen.queryByRole("button", { name: updateMessages.en.more })).toBeNull();
  });
  it.each(["lost", "conflict"])("preserves the desired preference after a %s save and requires an explicit authoritative check before another save", async mode => {
    let preferenceReads = 0, posts = 0;
    const mock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url === mine) return list();
      if (url === "/api/session/csrf") return Response.json({ csrf_token: "csrf" });
      if (init?.method !== "POST") return Response.json(pref(true, preferenceReads++ === 0 ? 0 : 4));
      posts++;
      if (posts === 1) { if (mode === "lost") throw new Error("Lost committed save"); return Response.json({}, { status: 409 }); }
      return Response.json(pref(false, 5));
    });
    vi.stubGlobal("fetch", mock); render(<Updates org={org} locale="en" />); await settle();
    fireEvent.click(screen.getByRole("checkbox")); await click(updateMessages.en.save);
    expect(screen.getByText(mode === "lost" ? updateMessages.en.preferenceCheck : updateMessages.en.conflict)).toBeTruthy();
    expect(screen.getByRole("checkbox")).toHaveProperty("checked", false);
    expect(screen.getByRole("button", { name: updateMessages.en.save })).toHaveProperty("disabled", true); expect(posts).toBe(1);
    await click(updateMessages.en.checkPreference);
    expect(screen.getByRole("checkbox")).toHaveProperty("checked", false);
    expect(screen.getByText(updateMessages.en.enabledNow)).toBeTruthy();
    await click(updateMessages.en.save); expect(posts).toBe(2);
    expect(mock.mock.calls.filter(call => call[1]?.method === "POST")[1][1]?.body).toBe('{"enabled":false,"expected_version":4}');
    expect(screen.getByText(updateMessages.en.saved)).toBeTruthy();
  });
  it("reconciles a lost read result through refresh without replaying the mutation", async () => {
    let lists = 0, posts = 0;
    const mock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url === mine) return list([item(++lists === 1 ? {} : { read_at: new Date().toISOString(), version: 2 })]);
      if (url === root + "/preference") return Response.json(pref());
      if (url === "/api/session/csrf") return Response.json({ csrf_token: "csrf" });
      if (init?.method === "POST") { posts++; throw new Error("Lost committed acknowledgement"); }
      throw new Error();
    });
    vi.stubGlobal("fetch", mock); render(<Updates org={org} locale="en" />); await settle();
    await click(updateMessages.en.markRead); expect(screen.getByText(updateMessages.en.readCheck)).toBeTruthy();
    expect(screen.getByRole("button", { name: updateMessages.en.markRead })).toHaveProperty("disabled", true);
    await click(updateMessages.en.refresh); expect(screen.getByText(updateMessages.en.read)).toBeTruthy(); expect(posts).toBe(1);
  });
  it("clears private content on revoked access and rejects a later preference response", async () => {
    let finish!: (value: Response) => void, reads = 0;
    const late = new Promise<Response>(resolve => { finish = resolve; });
    const mock = vi.fn(async (url: string) => url === mine ? ++reads === 1 ? list([item()]) : Response.json({}, { status: 403 }) : late);
    vi.stubGlobal("fetch", mock); render(<Updates org={org} locale="en" />); await settle();
    expect(screen.getAllByRole("article")).toHaveLength(1); await click(updateMessages.en.refresh);
    expect(screen.getByRole("alert").textContent).toBe(updateMessages.en.access); expect(screen.queryByRole("article")).toBeNull();
    await act(async () => { finish(Response.json(pref())); });
    expect(screen.queryByRole("checkbox")).toBeNull(); expect(screen.getByRole("link").getAttribute("href")).toBe("/en/account");
  });
  it("keeps the inbox usable when preference loading fails and retries the preference separately", async () => {
    let reads = 0;
    vi.stubGlobal("fetch", vi.fn(async (url: string) => url === mine ? list([item()]) : ++reads === 1 ? Response.json({}, { status: 503 }) : Response.json(pref())));
    render(<Updates org={org} locale="en" />); await settle();
    expect(screen.getByRole("article")).toBeTruthy(); expect(screen.getByText(updateMessages.en.preferenceError)).toBeTruthy();
    expect(screen.getByRole("button", { name: updateMessages.en.save })).toHaveProperty("disabled", true);
    await click(updateMessages.en.checkPreference); expect(screen.getByRole("checkbox")).toHaveProperty("disabled", false);
  });
  it("hides an expired notice without waiting for another action", async () => {
    vi.useFakeTimers(); vi.stubGlobal("fetch", vi.fn(async (url: string) => url === mine ? list([item({ expires_at: new Date(Date.now() + 1000).toISOString() })]) : Response.json(pref())));
    render(<Updates org={org} locale="en" />); await settle(); expect(screen.getByRole("article")).toBeTruthy();
    await act(async () => { await vi.advanceTimersByTimeAsync(1001); });
    expect(screen.queryByRole("article")).toBeNull(); expect(screen.getByText(updateMessages.en.empty)).toBeTruthy();
  });
  it("rejects an unknown action or template rather than rendering arbitrary content", async () => {
    vi.stubGlobal("fetch", vi.fn(async (url: string) => url === mine ? list([item({ action_kind: "outside" as "schedule" })]) : Response.json(pref())));
    render(<Updates org={org} locale="en" />); await settle();
    expect(screen.getByText(updateMessages.en.error)).toBeTruthy(); expect(screen.queryByRole("link")).toBeNull();
  });
  it("renders a complete Tamil empty state and retains loading correctness under StrictMode", async () => {
    const mock = vi.fn(async (url: string) => url === mine ? list() : Response.json(pref())); vi.stubGlobal("fetch", mock);
    render(<StrictMode><Updates org={org} locale="ta" /></StrictMode>); await settle();
    expect(screen.getByText(updateMessages.ta.empty)).toBeTruthy();
    expect(within(screen.getByRole("region", { name: updateMessages.ta.preferences })).getByRole("checkbox")).toBeTruthy();
    expect(Object.keys(updateMessages.en).sort()).toEqual(Object.keys(updateMessages.ta).sort());
  });
});
