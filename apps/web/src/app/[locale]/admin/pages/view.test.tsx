import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import Editor from "./view";

const org = "11111111-1111-4111-8111-111111111111";
const id = "22222222-2222-4222-8222-222222222222";
const base = `/api/cms/organizations/${org}/pages`;
const draft = {
  id, slug: "about-us", translations: [{
    id: "33333333-3333-4333-8333-333333333333", locale: "en", state: "draft", version: 4,
    title: "About us", body: "Our original content", seo_title: "", seo_description: "", published_revision_id: null,
  }],
};
function response(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));
}
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("publishing workspace", () => {
  it("validates and creates a new localized draft for the selected organization", async () => {
    const calls: Array<{ url: string; method: string; body?: string }> = [];
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input), method = init?.method ?? "GET";
      calls.push({ url, method, body: typeof init?.body === "string" ? init.body : undefined });
      if (url === base && method === "GET") return response({ items: [], next_cursor: null });
      if (url === "/api/session/csrf") return response({ csrf_token: "test-csrf" });
      if (url === base && method === "POST") return response(draft);
      return response({}, 500);
    }));
    render(<Editor org={org} locale="en" permissions={["cms.page.view", "cms.page.create"]} />);
    await screen.findByText("No pages yet.");
    const address = screen.getByLabelText("Page address", { exact: true }) as HTMLInputElement;
    expect(address.getAttribute("aria-describedby")).toBe("cms-address-help");
    expect(address.checkValidity()).toBe(false);
    fireEvent.change(address, { target: { value: "about-us" } });
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "About us" } });
    fireEvent.change(screen.getByLabelText("Content"), { target: { value: "Our original content" } });
    expect(address.checkValidity()).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(calls.some((call) => call.url === base && call.method === "POST")).toBe(true));
    expect(JSON.parse(calls.find((call) => call.url === base && call.method === "POST")!.body!)).toMatchObject({ slug: "about-us", title: "About us", body: "Our original content", locale: "en" });
  });

  it("saves and publishes the selected organization's current version with a CSRF token", async () => {
    const calls: Array<{ url: string; method: string; body?: string; headers?: HeadersInit }> = [];
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input), method = init?.method ?? "GET";
      calls.push({ url, method, body: typeof init?.body === "string" ? init.body : undefined, headers: init?.headers });
      if (url === "/api/session/csrf") return response({ csrf_token: "test-csrf" });
      if (url === base && method === "GET") return response({ items: [draft], next_cursor: null });
      if (url === `${base}/${id}`) return response(draft);
      if (url === `${base}/${id}/translations/en` && method === "PATCH") return response({ ...draft, translations: [{ ...draft.translations[0], body: "Updated content", version: 5 }] });
      if (url === `${base}/${id}/translations/en/publish` && method === "POST") return response({ ...draft, translations: [{ ...draft.translations[0], body: "Updated content", state: "published", version: 6 }] });
      return response({}, 500);
    }));
    render(<Editor org={org} locale="en" permissions={["cms.page.view", "cms.page.create", "cms.page.update", "cms.page.publish"]} />);
    fireEvent.click(await screen.findByRole("button", { name: /About us/ }));
    fireEvent.change(await screen.findByLabelText("Content"), { target: { value: "Updated content" } });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(calls.some((call) => call.method === "PATCH")).toBe(true));
    const update = calls.find((call) => call.method === "PATCH");
    expect(update?.url).toBe(`${base}/${id}/translations/en`);
    expect(JSON.parse(update!.body!)).toMatchObject({ body: "Updated content", expected_version: 4 });
    expect(update?.headers).toMatchObject({ "x-csrf-token": "test-csrf" });
    await screen.findByText(/v5/);
    fireEvent.click(screen.getByRole("button", { name: "Publish saved draft" }));
    await waitFor(() => expect(calls.some((call) => call.url.endsWith("/publish"))).toBe(true));
    expect(JSON.parse(calls.find((call) => call.url.endsWith("/publish"))!.body!)).toEqual({ expected_version: 5 });
  });

  it("previews the saved draft as text and does not enable publish without permission", async () => {
    const preview = { ...draft, translations: [{ ...draft.translations[0], body: "<script>alert('unsafe')</script>" }] };
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === base) return response({ items: [draft], next_cursor: null });
      if (url === `${base}/${id}`) return response(draft);
      if (url.endsWith("/preview")) return response(preview);
      return response({}, 500);
    }));
    const { container } = render(<Editor org={org} locale="en" permissions={["cms.page.view", "cms.page.update"]} />);
    fireEvent.click(await screen.findByRole("button", { name: /About us/ }));
    const publish = await screen.findByRole("button", { name: "Publish saved draft" });
    expect((publish as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Preview saved draft" }));
    expect(await screen.findByText("<script>alert('unsafe')</script>")).toBeTruthy();
    expect(container.querySelector("script")).toBeNull();
  });

  it("preserves unsaved work when page or language switching is cancelled", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === base) return response({ items: [draft], next_cursor: null });
      if (url === `${base}/${id}`) return response(draft);
      return response({}, 500);
    }));
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<Editor org={org} locale="en" permissions={["cms.page.view", "cms.page.create", "cms.page.update"]} />);
    fireEvent.click(await screen.findByRole("button", { name: /About us/ }));
    const content = await screen.findByLabelText("Content") as HTMLTextAreaElement;
    fireEvent.change(content, { target: { value: "Unsaved work" } });
    fireEvent.change(screen.getByLabelText("Content language"), { target: { value: "ta" } });
    expect(confirm).toHaveBeenCalled();
    expect(content.value).toBe("Unsaved work");
    expect((screen.getByLabelText("Content language") as HTMLSelectElement).value).toBe("en");
    fireEvent.click(within(screen.getByRole("complementary", { name: "Page library" })).getByRole("button", { name: "New page" }));
    expect(confirm).toHaveBeenCalledTimes(2);
    expect(content.value).toBe("Unsaved work");
  });

  it("prevents publishing or archiving over unsaved edits while keeping saved-draft preview available", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === base) return response({ items: [draft], next_cursor: null });
      if (url === `${base}/${id}`) return response(draft);
      return response({}, 500);
    }));
    render(<Editor org={org} locale="en" permissions={["cms.page.view", "cms.page.update", "cms.page.publish", "cms.page.archive"]} />);
    fireEvent.click(await screen.findByRole("button", { name: /About us/ }));
    fireEvent.change(await screen.findByLabelText("Content"), { target: { value: "Unsaved edits" } });
    expect((screen.getByRole("button", { name: "Publish saved draft" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Preview saved draft" }) as HTMLButtonElement).disabled).toBe(false);
    fireEvent.change(screen.getByLabelText("Archive reason"), { target: { value: "No longer current" } });
    expect((screen.getByRole("button", { name: "Archive" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("reports an optimistic concurrency conflict without losing the editor contents", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === base) return response({ items: [draft], next_cursor: null });
      if (url === `${base}/${id}`) return response(draft);
      if (url === "/api/session/csrf") return response({ csrf_token: "test-csrf" });
      if (init?.method === "PATCH") return response({}, 409);
      return response({}, 500);
    }));
    render(<Editor org={org} locale="en" permissions={["cms.page.view", "cms.page.update"]} />);
    fireEvent.click(await screen.findByRole("button", { name: /About us/ }));
    const content = await screen.findByLabelText("Content") as HTMLTextAreaElement;
    fireEvent.change(content, { target: { value: "My changes" } });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    expect(await screen.findByText("This page changed. Reload it before trying again.")).toBeTruthy();
    expect(content.value).toBe("My changes");
  });
});
