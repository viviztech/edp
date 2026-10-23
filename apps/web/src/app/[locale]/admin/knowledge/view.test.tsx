import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { components } from "../../../../lib/api-contracts";
import KnowledgeStaff from "./view";
import { words } from "../../knowledge/content";
import { org, resource, root, response, timestamp } from "../../knowledge/test-fixtures";

function mockApi(initial: ReturnType<typeof resource>[] = [], reject = false) {
  let items = initial; const writes: { body: Record<string, unknown>; url: string; method: string }[] = []; const reads: string[] = [];
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input); const [path] = url.split("?");
    if (url === "/api/session/csrf") return response({ csrf_token: "csrf" });
    if (!init?.method) {
      reads.push(url);
      if (path.endsWith("/history")) return response({ items: [], next_cursor: null });
      if (path === `${root}/items`) return response({ items, next_cursor: null });
      if (path === `${root}/funding-cases`) return response({ items: [], next_cursor: null });
      return response(items[0]);
    }
    expect(new Headers(init.headers).get("x-csrf-token")).toBe("csrf");
    const body = JSON.parse(String(init.body)) as Record<string, unknown>; writes.push({ body, url, method: init.method });
    if (reject) return response({}, 409);
    const creating = path === `${root}/items`;
    const allowed = creating ? Object.keys(resource()).filter((key) => !["id", "state", "version", "published_at", "updated_at", "availability"].includes(key))
      : init.method === "PATCH" ? [...Object.keys(body).filter((key) => !["id", "state", "version", "published_at", "updated_at", "availability"].includes(key))]
      : ["expected_version", "reason"];
    expect(Object.keys(body).every((key) => allowed.includes(key))).toBe(true);
    const item = creating ? resource({ ...body as Partial<components["schemas"]["KnowledgeView"]>, state: "draft", version: 1, published_at: null })
      : { ...items[0], ...(init.method === "PATCH" ? body : {}), state: path.endsWith("/publish") ? "published" : path.endsWith("/archive") ? "archived" : path.endsWith("/draft") ? "draft" : items[0].state,
        version: items[0].version + 1, updated_at: timestamp } as ReturnType<typeof resource>;
    items = [item]; return response(item, creating ? 201 : 200);
  });
  vi.stubGlobal("fetch", fetchMock); return { writes, reads };
}
function fillForm(kind: "scheme" | "funding" | "opportunity") {
  const form = screen.getByRole("form", { name: "Resource editor" });
  fireEvent.change(within(form).getByLabelText("Resource kind"), { target: { value: kind } });
  const values = { Slug: `synthetic-${kind}`, Title: `Synthetic ${kind}`, Provider: "Example provider", Type: "Program", Description: "Official synthetic description",
    Eligibility: "Read official criteria", Sector: "Services", Geography: "Tamil Nadu", "Application process": "Apply with official provider",
    "Official source URL": "https://example.gov.in/synthetic" };
  for (const [label, value] of Object.entries(values)) fireEvent.change(within(form).getByLabelText(label), { target: { value } });
  return form;
}
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("staff resource management", () => {
  it.each(["scheme", "funding", "opportunity"] as const)("creates and explicitly publishes a %s with source evidence and exact version", async (kind) => {
    const api = mockApi(); render(<KnowledgeStaff org={org} locale="en" canManage canFunding />);
    await waitFor(() => expect((screen.getByRole("button", { name: "Create draft" }) as HTMLButtonElement).disabled).toBe(false));
    const form = fillForm(kind); fireEvent.submit(form);
    await screen.findByText("Saved.");
    expect(api.writes[0].body.kind).toBe(kind); expect(api.writes[0].body.official_url).toBe("https://example.gov.in/synthetic");
    expect((screen.getByRole("button", { name: "Publish resource" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(screen.getByLabelText("Reason for change"), { target: { value: "Official evidence verified" } });
    fireEvent.click(screen.getByRole("button", { name: "Publish resource" }));
    await waitFor(() => expect(api.writes.length).toBe(2));
    expect(api.writes[1].body).toEqual({ expected_version: 1, reason: "Official evidence verified" });
    await waitFor(() => expect(screen.getByRole("button", { name: "Return to draft" })).toBeTruthy());
    expect((screen.getByLabelText("Title") as HTMLInputElement).closest("fieldset")?.disabled).toBe(true);
  });

  it("requires saving unsaved content before publishing and whitelists update fields", async () => {
    const api = mockApi([resource({ state: "draft", version: 3 })]);
    render(<KnowledgeStaff org={org} locale="en" canManage canFunding={false} />);
    fireEvent.click(await screen.findByRole("button", { name: "Edit resource" }));
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "New draft title" } });
    fireEvent.change(screen.getByLabelText("Reason for change"), { target: { value: "Correct provider title" } });
    expect((screen.getByRole("button", { name: "Publish resource" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByLabelText("Slug") as HTMLInputElement).disabled).toBe(true);
    fireEvent.submit(screen.getByRole("form", { name: "Resource editor" }));
    await screen.findByText("Saved.");
    expect(api.writes[0].body.title).toBe("New draft title");
    expect(api.writes[0].body.expected_version).toBe(3);
    for (const metadata of ["id", "state", "version", "updated_at", "published_at", "availability"]) expect(api.writes[0].body).not.toHaveProperty(metadata);
    fireEvent.change(screen.getByLabelText("Reason for change"), { target: { value: "Publish corrected version" } });
    fireEvent.click(screen.getByRole("button", { name: "Publish resource" }));
    await waitFor(() => expect(api.writes[1].body.expected_version).toBe(4));
  });

  it("keeps a rejected edit and reason through an explicit current-version refresh", async () => {
    const api = mockApi([resource({ state: "draft" })], true);
    render(<KnowledgeStaff org={org} locale="en" canManage canFunding={false} />);
    fireEvent.click(await screen.findByRole("button", { name: "Edit resource" }));
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Unsaved local title" } });
    fireEvent.change(screen.getByLabelText("Reason for change"), { target: { value: "Unsaved correction reason" } });
    fireEvent.submit(screen.getByRole("form", { name: "Resource editor" }));
    fireEvent.click(await screen.findByRole("button", { name: "Refresh saved resource" }));
    await screen.findByText(words.en.refreshed);
    expect((screen.getByLabelText("Title") as HTMLInputElement).value).toBe("Unsaved local title");
    expect((screen.getByLabelText("Reason for change") as HTMLTextAreaElement).value).toBe("Unsaved correction reason");
    expect(api.writes.length).toBe(1);
  });

  it("loads Tamil and closed entries for management and renders a funding-only role without an authoring form", async () => {
    const api = mockApi(); const view = render(<KnowledgeStaff org={org} locale="ta" canManage canFunding={false} />);
    await waitFor(() => expect(api.reads.some((url) => url.includes("locale=ta") && url.includes("availability=all"))).toBe(true));
    expect(screen.getByRole("heading", { name: "வளத் திருத்தி" })).toBeTruthy(); view.unmount();
    render(<KnowledgeStaff org={org} locale="en" canManage={false} canFunding />);
    await screen.findByText("No funding cases in this organization.");
    expect(screen.queryByRole("form", { name: "Resource editor" })).toBeNull();
  });

  it("asks before replacing unsaved content and honors cancellation", async () => {
    mockApi([resource()]); vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<KnowledgeStaff org={org} locale="en" canManage canFunding={false} />);
    await screen.findByRole("button", { name: "Edit resource" });
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Unfinished new resource" } });
    fireEvent.click(screen.getByRole("button", { name: "Edit resource" }));
    expect(window.confirm).toHaveBeenCalledOnce();
    expect((screen.getByLabelText("Title") as HTMLInputElement).value).toBe("Unfinished new resource");
  });
});
