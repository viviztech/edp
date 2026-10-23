import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { POST } from "./route";
const org = "11111111-1111-4111-8111-111111111111", reference = "22222222-2222-4222-8222-222222222222";
vi.mock("next/headers", () => ({ cookies: async () => ({ get: () => ({ value: "csrf" }) }) }));
vi.mock("../../../../lib/server-api", () => ({ csrfName: "edp_csrf", settings: () => ({ api: "http://api", key: "private-server-key", origin: "http://localhost:3000" }) }));
const policy = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock("../../../../lib/public-enquiries", () => ({ publicEnquirySettings: () => ({ organization: "11111111-1111-4111-8111-111111111111" }), publicEnquiryPolicy: policy.get }));
const body = { name: "Synthetic", email: "enquirer@example.test", phone: "", message: "தமிழ் விசாரணை", consent_version: "v1", consent: true, locale: "ta", website: "" };
function request(value: BodyInit = JSON.stringify(body), origin = "http://localhost:3000", query = "") {
  return new NextRequest("http://localhost:3000/api/enquiries/public" + query, { method: "POST", body: value,
    headers: { origin, "content-type": "application/json", "x-csrf-token": "csrf", "x-forwarded-for": "192.0.2.1", "x-bff-key": "attacker", "x-browser-session": "attacker" } });
}
afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });
describe("public enquiry proxy", () => {
  it("rejects cross-origin, query injection and unapproved consent before an upstream write", async () => {
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    expect((await POST(request(undefined, "https://evil.test"))).status).toBe(403);
    expect((await POST(request(undefined, undefined, "?organization=evil"))).status).toBe(400);
    expect((await POST(request(JSON.stringify({ ...body, consent: false })))).status).toBe(400);
    expect((await POST(request(JSON.stringify({ ...body, website: "bot" })))).status).toBe(400);
    expect((await POST(request(JSON.stringify({ ...body, organization: org })))).status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("bounds UTF-8 byte streams, rejects malformed encoding and keeps payloads out of errors", async () => {
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    expect((await POST(request(JSON.stringify({ ...body, message: "த".repeat(11000) })))).status).toBe(413);
    expect((await POST(request(new Uint8Array([0xff, 0xfe])))).status).toBe(400);
    expect((await POST(request("{"))).status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("requires a live approved policy and blocks stale notice versions", async () => {
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    policy.get.mockResolvedValueOnce(null).mockResolvedValueOnce({ consent_version: "v2" });
    expect((await POST(request())).status).toBe(503);
    const stale = await POST(request()); expect(stale.status).toBe(422); expect((await stale.json()).error.code).toBe("consent_required");
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("uses the server organization and key, excludes browser/forwarded headers and returns only the receipt", async () => {
    policy.get.mockResolvedValue({ consent_version: "v1" });
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ accepted: true, reference, email: "must-not-leak@example.test" }), { status: 202 })); vi.stubGlobal("fetch", fetchMock);
    const response = await POST(request()); expect(response.status).toBe(202); expect(await response.json()).toEqual({ accepted: true, reference });
    expect(response.headers.get("cache-control")).toBe("no-store"); expect(response.headers.get("set-cookie")).toBeNull();
    const [url, init] = fetchMock.mock.calls[0]; expect(url).toBe(`http://api/api/v1/public/organizations/${org}/enquiries`);
    expect(init.headers).toEqual({ "Content-Type": "application/json", "X-BFF-Key": "private-server-key" });
    expect(JSON.parse(init.body)).toEqual({ name: body.name, email: body.email, phone: "", message: body.message, consent_version: "v1" });
  });
});
