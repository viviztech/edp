import { afterEach, describe, expect, it, vi } from "vitest";
import ApplicationsPage from "./page";

const { serverApi, notFound, redirect } = vi.hoisted(() => ({
  serverApi: vi.fn(),
  notFound: vi.fn((): never => { throw new Error("not_found"); }),
  redirect: vi.fn((url: string): never => { throw new Error(`redirect:${url}`); }),
}));
vi.mock("../../../lib/server-api", () => ({ serverApi }));
vi.mock("next/navigation", () => ({ notFound, redirect }));
vi.mock("./view", () => ({ default: () => null }));

const organization = "11111111-1111-4111-8111-111111111111";
const cycle = "22222222-2222-4222-8222-222222222222";
const page = (query: Record<string, string | string[] | undefined> = {}) => ApplicationsPage({
  params: Promise.resolve({ locale: "en" }), searchParams: Promise.resolve(query),
});
afterEach(() => { vi.clearAllMocks(); vi.unstubAllEnvs(); });

describe("application destination boundaries", () => {
  it("preserves validated organization and intake through sign-in", async () => {
    serverApi.mockResolvedValue(new Response(null, { status: 401 }));
    await expect(page({ organization, cycle, returnTo: "https://example.com" })).rejects.toThrow("redirect:");
    expect(redirect).toHaveBeenCalledWith(`/en/account?organization=${organization}&cycle=${cycle}`);
  });

  it.each([{ organization: [organization, organization] }, { organization: "bad" }, { organization, cycle: "bad" }, { organization, cycle: [cycle, cycle] }])("rejects malformed or duplicated explicit context %j", async (query) => {
    await expect(page(query)).rejects.toThrow("not_found");
    expect(serverApi).not.toHaveBeenCalled();
  });

  it("rejects an intake with no valid organization instead of selecting another one", async () => {
    vi.stubEnv("PUBLIC_ORGANIZATION_ID", "");
    await expect(page({ cycle })).rejects.toThrow("not_found");
  });

  it("allows authenticated applicants to open global history without an organization", async () => {
    vi.stubEnv("PUBLIC_ORGANIZATION_ID", "");
    serverApi.mockResolvedValue(new Response("{}"));
    const result = await page();
    expect(result.props.id).toBe("main");
    expect(result.props.children.props.org).toBeUndefined();
  });
});
