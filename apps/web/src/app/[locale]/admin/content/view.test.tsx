import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { components } from "../../../../lib/api-contracts";
import { editorialAdminMessages } from "../../../../lib/editorial-admin-messages";
import EditorialWorkspace from "./view";

type Entry = components["schemas"]["EditorialView"];
const org = "11111111-1111-4111-8111-111111111111";
const id = "22222222-2222-4222-8222-222222222222";
const base = `/api/cms/organizations/${org}/editorial`;
const permissions = ["view", "create", "update", "publish", "archive"].map(action => `cms.editorial.${action}`);
const fixture = (overrides: Partial<Entry> = {}): Entry => ({ id, kind: "news", locale: "en", slug: "synthetic-news", title: "Original title", body: "Original body", starts_at: null, ends_at: null, sort_order: 0, state: "draft", version: 1, published_at: null, ...overrides });
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const click = async (name: string | RegExp) => { await act(async () => { fireEvent.click(screen.getByRole("button", { name })); }); };
const change = (name: string, value: string) => fireEvent.change(screen.getByLabelText(name), { target: { value } });
const value = (name: string) => (screen.getByLabelText(name) as HTMLInputElement).value;
const submit = async () => { await act(async () => { fireEvent.submit(screen.getByLabelText("Title").closest("form")!); }); };

function mockApi(initial = fixture()) {
  const api = {
    entry: initial,
    writes: [] as { path: string; body: Record<string, unknown>; method: string }[],
    mutation: null as null | (() => Promise<Response>),
    lookup: null as null | (() => Promise<Response>),
    requests: [] as string[],
  };
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input); api.requests.push(path);
    if (path === "/api/session/csrf") return json({ csrf_token: "test-csrf" });
    if (!init?.method || init.method === "GET") {
      if (path.includes("?")) {
        if (new URL(path, "http://local").searchParams.has("slug") && api.lookup) return api.lookup();
        return json({ items: [api.entry], next_cursor: null });
      }
      if (path === `${base}/${id}`) return json(api.entry);
      throw new Error(`Unexpected read ${path}`);
    }
    expect(new Headers(init.headers).get("x-csrf-token")).toBe("test-csrf");
    const body = JSON.parse(String(init.body));
    api.writes.push({ path, body, method: init.method });
    if (api.mutation) return api.mutation();
    if (path === base) api.entry = fixture({ ...body, id });
    else if (init.method === "PATCH") api.entry = { ...api.entry, ...body, version: api.entry.version + 1 };
    else api.entry = { ...api.entry, state: path.endsWith("publish") ? "published" : path.endsWith("archive") ? "archived" : "draft", version: api.entry.version + 1 };
    return json(api.entry);
  }));
  return api;
}
async function open(initial = fixture(), rights = permissions, locale: "en" | "ta" = "en") {
  const api = mockApi(initial);
  await act(async () => { render(<EditorialWorkspace org={org} locale={locale} permissions={rights} />); });
  await click(new RegExp(initial.title));
  return api;
}
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("editorial authoring and recovery", () => {
  it("reconciles a committed create whose response was lost without resending or overwriting", async () => {
    const api = mockApi();
    await act(async () => { render(<EditorialWorkspace org={org} locale="en" permissions={permissions} />); });
    await click("New entry");
    change("Content address", "new-entry"); change("Title", "Kept title"); change("Content", "Kept body");
    api.mutation = async () => { api.entry = fixture({ slug: "new-entry", title: "Kept title", body: "Kept body" }); throw new Error("response lost after commit"); };
    await submit();
    expect(value("Content")).toBe("Kept body");
    expect(screen.getByRole("status").textContent).toContain("save could not be confirmed");
    expect(screen.getByLabelText("Title").matches(":disabled")).toBe(true);
    await submit();
    expect(api.writes).toHaveLength(1);
    await click("Check this address");
    expect(api.requests.at(-1)).toBe(`${base}?kind=news&locale=en&slug=new-entry&limit=1`);
    expect(screen.getByRole("heading", { name: "Kept title" })).toBeTruthy();
    expect(api.writes).toHaveLength(1);
    await click("Use stored version and keep my draft");
    expect(value("Content")).toBe("Kept body");
    expect(screen.getByRole("button", { name: "Save draft" }).matches(":disabled")).toBe(true);
    expect(api.writes).toHaveLength(1);
  });

  it("permits an explicit retry only after the bounded address check found no entry", async () => {
    const api = mockApi();
    await act(async () => { render(<EditorialWorkspace org={org} locale="en" permissions={permissions} />); });
    await click("New entry");
    change("Content address", "new-entry"); change("Title", "Kept title"); change("Content", "Kept body");
    api.mutation = async () => json({}, 503);
    await submit();
    api.lookup = async () => json({ items: [], next_cursor: null });
    await click("Check this address");
    expect(screen.getByRole("status").textContent).toContain("No entry was found");
    expect(screen.getByLabelText("Title").matches(":disabled")).toBe(false);
    expect(api.writes).toHaveLength(1);
    api.mutation = null;
    await submit();
    expect(api.writes).toHaveLength(2);
    expect(api.writes[1]).toMatchObject({ path: base, method: "POST", body: { slug: "new-entry", title: "Kept title", body: "Kept body" } });
  });

  it("compares a genuine duplicate without claiming it or changing the stored entry", async () => {
    const api = mockApi();
    await act(async () => { render(<EditorialWorkspace org={org} locale="en" permissions={permissions} />); });
    await click("New entry");
    change("Content address", "synthetic-news"); change("Title", "My different title"); change("Content", "My different body");
    api.mutation = async () => json({ error: { code: "content_conflict" } }, 409);
    await submit();
    expect(screen.getByLabelText("Content address").matches(":disabled")).toBe(false);
    await click("Check this address");
    expect(screen.getByRole("heading", { name: "Original title" })).toBeTruthy();
    expect(value("Content")).toBe("My different body");
    expect(api.entry.body).toBe("Original body");
    expect(api.writes).toHaveLength(1);
    await click("Choose another address");
    expect(value("Content")).toBe("My different body");
    change("Content address", "different-address");
    api.mutation = null;
    await submit();
    expect(api.writes[1]).toMatchObject({ path: base, method: "POST", body: { slug: "different-address" } });
    expect(api.writes.every(write => write.method === "POST")).toBe(true);
  });
  it("saves with the selected version and publishes only the saved draft", async () => {
    const api = await open();
    change("Title", "Revised title");
    expect(screen.getByRole("button", { name: "Publish saved draft" }).matches(":disabled")).toBe(true);
    expect(screen.getByRole("button", { name: /Original title/ }).matches(":disabled")).toBe(true);
    await submit();
    expect(api.writes[0]).toMatchObject({ path: `${base}/${id}`, method: "PATCH", body: { expected_version: 1, title: "Revised title", body: "Original body" } });
    await click("Publish saved draft");
    expect(api.writes[1].body).toEqual({ expected_version: 2 });
    expect(screen.getByRole("link", { name: "View published entry" }).getAttribute("href")).toBe("/en/content/news/synthetic-news");
    expect(screen.getByLabelText("Title").matches(":disabled")).toBe(true);
  });

  it("keeps a failed local draft and explicitly reviews the latest server version before retrying", async () => {
    const api = await open();
    change("Title", "Local title");
    api.mutation = async () => json({ error: { code: "version_conflict" } }, 409);
    await submit();
    expect(value("Title")).toBe("Local title");
    expect(screen.getByRole("status").textContent).toContain("Your local draft has been kept");
    api.entry = fixture({ title: "Remote title", version: 2 });
    await click("Load latest values");
    expect(value("Title")).toBe("Local title");
    expect(screen.getByRole("heading", { name: "Remote title" })).toBeTruthy();
    await click("Use latest version and keep my changes");
    expect(value("Title")).toBe("Local title");
    api.mutation = null;
    await submit();
    expect(api.writes[1].body.expected_version).toBe(2);
    expect(api.writes[1].body.title).toBe("Local title");
  });

  it("keeps local changes when a concurrent publication requires archive and restore before editing", async () => {
    const api = await open();
    change("Title", "Local title");
    api.mutation = async () => json({ error: { code: "published_entry_read_only" } }, 409);
    await submit();
    api.entry = fixture({ state: "published", version: 2 });
    await click("Load latest values"); await click("Use latest version and keep my changes");
    expect(screen.getByLabelText("Title").matches(":disabled")).toBe(true);
    api.mutation = null;
    change("Archive reason", "Prepare a revised draft");
    await click("Archive");
    expect(value("Title")).toBe("Local title");
    await click("Restore draft");
    expect(value("Title")).toBe("Local title");
    expect(screen.getByLabelText("Title").matches(":disabled")).toBe(false);
    await submit();
    expect(api.writes.at(-1)?.body).toMatchObject({ expected_version: 4, title: "Local title" });
  });

  it("freezes controls and prevents duplicate writes while a mutation is pending", async () => {
    const api = await open();
    change("Title", "Pending title");
    let resolve!: (response: Response) => void;
    api.mutation = () => new Promise<Response>(yes => { resolve = yes; });
    await submit();
    expect(screen.getByLabelText("Title").matches(":disabled")).toBe(true);
    expect(screen.getByLabelText("Content language").matches(":disabled")).toBe(true);
    await submit();
    expect(api.writes).toHaveLength(1);
    await act(async () => { resolve(json(fixture({ title: "Pending title", version: 2 }))); });
    expect(value("Title")).toBe("Pending title");
  });

  it("preserves draft data on network errors and rejects reversed dates without writing", async () => {
    const api = await open();
    change("Content", "Locally edited content");
    change("Starts at (UTC)", "2026-10-24T08:00"); change("Ends at (UTC)", "2026-10-23T08:00");
    await submit();
    expect(api.writes).toHaveLength(0);
    expect(screen.getByRole("status").textContent).toContain("end after the start");
    change("Ends at (UTC)", "2026-10-24T10:00");
    api.mutation = async () => { throw new Error("network"); };
    await submit();
    expect(value("Content")).toBe("Locally edited content");
    expect(screen.getByLabelText("Content").matches(":disabled")).toBe(false);
  });

  it("creates a separate Tamil draft and allows correcting a duplicate address without losing content", async () => {
    const api = mockApi(fixture({ locale: "ta" }));
    await act(async () => { render(<EditorialWorkspace org={org} locale="ta" permissions={permissions} />); });
    await click(editorialAdminMessages.ta.newEntry);
    change(editorialAdminMessages.ta.slug, "synthetic-tamil"); change(editorialAdminMessages.ta.titleField, "தமிழ் செய்தி"); change(editorialAdminMessages.ta.body, "தமிழ் உள்ளடக்கம்");
    api.mutation = async () => json({ error: { code: "content_conflict" } }, 409);
    await act(async () => { fireEvent.submit(screen.getByLabelText(editorialAdminMessages.ta.titleField).closest("form")!); });
    expect(value(editorialAdminMessages.ta.body)).toBe("தமிழ் உள்ளடக்கம்");
    expect(screen.getByLabelText(editorialAdminMessages.ta.slug).matches(":disabled")).toBe(false);
    change(editorialAdminMessages.ta.slug, "another-tamil-address"); api.mutation = null;
    await act(async () => { fireEvent.submit(screen.getByLabelText(editorialAdminMessages.ta.titleField).closest("form")!); });
    expect(api.writes[1].body).toMatchObject({ locale: "ta", kind: "news", slug: "another-tamil-address", body: "தமிழ் உள்ளடக்கம்" });
  });

  it("uses actual scoped rights for authoring and lifecycle controls", async () => {
    await open(fixture(), ["cms.editorial.view"]);
    expect(screen.getByRole("button", { name: "New entry" }).matches(":disabled")).toBe(true);
    expect(screen.getByLabelText("Title").matches(":disabled")).toBe(true);
    expect(screen.queryByRole("button", { name: "Publish saved draft" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Archive" })).toBeNull();
  });
});
