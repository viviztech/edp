import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { serverApi } from "../lib/server-api";
import ContentAdminPage from "../app/[locale]/admin/content/page";
import MediaAdminPage from "../app/[locale]/admin/media/page";
vi.mock("../lib/server-api", () => ({ serverApi: vi.fn() }));
vi.mock("next/navigation", () => ({ notFound: () => { throw new Error("not found"); }, redirect: (path: string) => { throw new Error(`redirect:${path}`); } }));
vi.mock("../app/[locale]/admin/content/view", () => ({ default: () => <div data-testid="workspace" /> }));
vi.mock("../app/[locale]/admin/media/view", () => ({ default: () => <div data-testid="workspace" /> }));
const organization = "11111111-1111-4111-8111-111111111111";
const foreign = "22222222-2222-4222-8222-222222222222";
const profile = (permissions: string[]) => new Response(JSON.stringify({ id: "person", grants: [{ organization_id: organization, organization_name: "Synthetic content", permissions }] }));
beforeEach(() => { vi.mocked(serverApi).mockImplementation(async () => profile(["cms.editorial.view", "cms.asset.view"])); });
afterEach(() => { cleanup(); vi.resetAllMocks(); });
const pages = [["content", ContentAdminPage, "cms.editorial.view"], ["media", MediaAdminPage, "cms.asset.view"]] as const;
describe("content and media server boundaries", () => {
  it.each(pages)("selects the scoped organization for %s and renders a focusable Tamil skip target", async (route, Page) => {
    render(await Page({ params: Promise.resolve({ locale: "ta" }), searchParams: Promise.resolve({ organization }) }));
    expect(screen.getByTestId("workspace")).toBeTruthy();
    expect(screen.getByRole("main").getAttribute("tabindex")).toBe("-1");
    expect(screen.getAllByRole("link").find(link => link.getAttribute("aria-current") === "page")?.getAttribute("href")).toBe(`/ta/admin/${route}?organization=${organization}`);
  });
  it.each(pages)("never substitutes an authorized organization for requested foreign %s scope", async (_route, Page) => {
    render(await Page({ params: Promise.resolve({ locale: "en" }), searchParams: Promise.resolve({ organization: foreign }) }));
    expect(screen.queryByTestId("workspace")).toBeNull();
  });
  it.each(pages)("requires the specific %s view permission rather than system/create rights", async (_route, Page) => {
    vi.mocked(serverApi).mockResolvedValue(profile(["system.access", "cms.editorial.create", "cms.asset.publish"]));
    render(await Page({ params: Promise.resolve({ locale: "en" }), searchParams: Promise.resolve({ organization }) }));
    expect(screen.queryByTestId("workspace")).toBeNull();
  });
  it.each(pages)("redirects unauthenticated %s users to localized account entry", async (_route, Page) => {
    vi.mocked(serverApi).mockResolvedValue(new Response(null, { status: 401 }));
    await expect(Page({ params: Promise.resolve({ locale: "ta" }), searchParams: Promise.resolve({ organization }) })).rejects.toThrow("redirect:/ta/account");
  });
});
