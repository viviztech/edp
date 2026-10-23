import { afterEach, describe, expect, it, vi } from "vitest";
import { publicEditorial, publicEditorialItem } from "./public-editorial";
vi.mock("server-only", () => ({}));
const org = "11111111-1111-4111-8111-111111111111";
const cursor = "22222222-2222-4222-8222-222222222222";
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });
describe("public editorial requests", () => {
  it("forwards only known kind, locale and bounded cursor without staff credentials", async () => {
    vi.stubEnv("PUBLIC_ORGANIZATION_ID", org); vi.stubEnv("API_INTERNAL_URL", "http://api/");
    const mock = vi.fn().mockImplementation(async () => new Response(JSON.stringify({ items: [], next_cursor: null }))); vi.stubGlobal("fetch", mock);
    await publicEditorial("event", "ta", cursor);
    expect(mock.mock.calls[0][0]).toBe(`http://api/api/v1/public/organizations/${org}/editorial?locale=ta&kind=event&limit=25&cursor=${cursor}`);
    expect(mock.mock.calls[0][1]).toMatchObject({ cache: "no-store" });
    expect(mock.mock.calls[0][1].headers).toBeUndefined();
    await publicEditorialItem("news", "synthetic-news", "en");
    expect(mock.mock.calls[1][0]).toBe(`http://api/api/v1/public/organizations/${org}/editorial/news/synthetic-news?locale=en`);
  });
  it("rejects malformed cursors and locales before calling the API", async () => {
    const mock = vi.fn(); vi.stubGlobal("fetch", mock);
    await expect(publicEditorial("news", "en", "//outside.example")).rejects.toThrow("Invalid public content query");
    await expect(publicEditorial("news", "fr")).rejects.toThrow("Invalid public content query");
    expect(await publicEditorialItem("news", "../admin", "en")).toBeNull();
    expect(mock).not.toHaveBeenCalled();
  });
});
