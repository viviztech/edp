import { afterEach, describe, expect, it, vi } from "vitest";
import { publicEnquiryPolicy, publicEnquirySettings } from "./public-enquiries";
vi.mock("server-only", () => ({}));
const organization = "11111111-1111-4111-8111-111111111111";
const approved = { enabled: true, consent_version: "synthetic-v1", consent_text: "Synthetic test consent", privacy_notice_url: "/ta/pages/privacy" };
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });
function configure() { vi.stubEnv("PUBLIC_ORGANIZATION_ID", organization); vi.stubEnv("API_INTERNAL_URL", "http://api/"); }
describe("server enquiry policy boundary", () => {
  it("keeps forms unavailable without a valid provisioned organization", async () => {
    vi.stubEnv("PUBLIC_ORGANIZATION_ID", "../../auth"); vi.stubEnv("API_INTERNAL_URL", "http://api");
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    expect(publicEnquirySettings()).toBeNull(); expect(await publicEnquiryPolicy("en")).toBeNull(); expect(fetchMock).not.toHaveBeenCalled();
  });
  it("loads only public localized policy, without session or server secrets", async () => {
    configure(); const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(approved))); vi.stubGlobal("fetch", fetchMock);
    expect(await publicEnquiryPolicy("ta")).toEqual(approved);
    const [url, init] = fetchMock.mock.calls[0]; expect(url).toBe(`http://api/api/v1/public/organizations/${organization}/enquiry-policy?locale=ta`);
    expect(init.cache).toBe("no-store"); expect(init.headers).toBeUndefined();
  });
  it("fails closed when disabled, unapproved, malformed, or unavailable", async () => {
    configure(); const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    for (const value of [{ ...approved, enabled: false }, { ...approved, consent_text: " " }, { ...approved, privacy_notice_url: "javascript:alert(1)" }, { ...approved, consent_version: "x".repeat(41) }, { ...approved, consent_text: "x".repeat(2001) }]) {
      fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(value))); expect(await publicEnquiryPolicy("en")).toBeNull();
    }
    fetchMock.mockRejectedValueOnce(new Error("offline")); expect(await publicEnquiryPolicy("en")).toBeNull();
  });
});
