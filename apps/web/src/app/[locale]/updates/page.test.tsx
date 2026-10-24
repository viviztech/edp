import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { serverApi } from "../../../lib/server-api";
import Page from "./page";
vi.mock("../../../lib/server-api", () => ({ serverApi: vi.fn() }));
vi.mock("next/navigation", () => ({ notFound: () => { throw new Error("not_found"); }, redirect: (path: string) => { throw new Error(`redirect:${path}`); } }));
vi.mock("./view", () => ({ default: ({ org }: { org: string }) => <div data-testid="inbox">{org}</div> }));
const org = "11111111-1111-4111-8111-111111111111", other = "22222222-2222-4222-8222-222222222222";
const props = (organization: string | string[] | undefined = org, locale = "en") => ({ params: Promise.resolve({ locale }), searchParams: Promise.resolve({ organization }) });
const profile = (permissions: string[] = ["participant.self"]) => Response.json({ id: "person", grants: [{ organization_id: org, organization_name: "Synthetic program", permissions }] });
afterEach(() => { cleanup(); vi.resetAllMocks(); });
describe("participant updates page", () => {
  it("uses current participant access independently of CRM and supplies a focusable scoped navigation", async () => {
    vi.mocked(serverApi).mockResolvedValue(profile()); render(await Page(props(org, "ta")));
    expect(screen.getByTestId("inbox").textContent).toBe(org); expect(screen.getByRole("main").getAttribute("tabindex")).toBe("-1");
    expect(screen.getByRole("link", { name: "எனது அறிவிப்புகள்" }).getAttribute("aria-current")).toBe("page");
    expect(vi.mocked(serverApi).mock.calls).toEqual([["/auth/me"]]);
  });
  it("does not grant participant updates to CRM staff or fall back from a foreign organization", async () => {
    vi.mocked(serverApi).mockImplementation(async () => profile(["crm.lead.view", "system.access"])); render(await Page(props()));
    expect(screen.queryByTestId("inbox")).toBeNull(); cleanup();
    vi.mocked(serverApi).mockImplementation(async () => profile()); render(await Page(props(other)));
    expect(screen.queryByTestId("inbox")).toBeNull();
  });
  it.each(["malformed", [org, other]])("rejects malformed or repeated organization selection", async organization => {
    await expect(Page(props(organization))).rejects.toThrow("not_found"); expect(serverApi).not.toHaveBeenCalled();
  });
  it("redirects an expired session and shows a usable unavailable account response", async () => {
    vi.mocked(serverApi).mockResolvedValueOnce(Response.json({}, { status: 401 })); await expect(Page(props())).rejects.toThrow("redirect:/en/account");
    vi.mocked(serverApi).mockRejectedValueOnce(new Error("offline")); render(await Page(props())); expect(screen.getByRole("alert")).toBeTruthy(); expect(screen.getByRole("link").getAttribute("href")).toBe("/en/account");
  });
});
