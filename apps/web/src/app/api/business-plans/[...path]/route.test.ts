// @vitest-environment node
import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { POST } from "./route";

vi.mock("next/headers", () => ({ cookies: async () => ({
  get: (name: string) => ({ value: name === "csrf" ? "csrf-token" : "browser-session" }),
}) }));
vi.mock("../../../../lib/server-api", () => ({
  cookieName: "session", csrfName: "csrf",
  settings: () => ({ origin: "http://localhost:3000", api: "http://api.internal", key: "test-key" }),
}));

const org = "123e4567-e89b-42d3-a456-426614174000";
const id = "123e4567-e89b-42d3-a456-426614174001";
async function send(path: string[], body: string, csrf = "csrf-token") {
  return POST(new NextRequest("http://localhost:3000/api/business-plans/" + path.join("/"), {
    method: "POST", headers: { origin: "http://localhost:3000", "Content-Type": "application/json", "x-csrf-token": csrf }, body,
  }), { params: Promise.resolve({ path }) });
}
afterEach(() => vi.unstubAllGlobals());

describe("business-plan proxy text bounds", () => {
  it("forwards all 20 maximum-length comments with JSON escape expansion", async () => {
    const codes = ["executive_summary", "problem", "solution", "product_service", "customer_segments", "market", "competition",
      "value_proposition", "business_model", "pricing", "sales_marketing", "operations", "team", "investment",
      "revenue_assumptions", "expense_assumptions", "break_even_inputs", "funding_requirement", "risks", "milestones"];
    const payload = { expected_version: 22, decision: "changes_requested", reason: "Review evidence",
      comments: Object.fromEntries(codes.map((code) => [code, "\u0001".repeat(1999) + "x"])) };
    const body = JSON.stringify(payload);
    expect(body.length).toBeGreaterThan(16384);
    const upstream = vi.fn(async () => Response.json({ id }));
    vi.stubGlobal("fetch", upstream);
    const response = await send(["organizations", org, "submissions", id, "review"], body);
    expect(response.status).toBe(200);
    expect(upstream).toHaveBeenCalledOnce();
    expect(upstream).toHaveBeenCalledWith(`http://api.internal/api/v1/business-plans/organizations/${org}/submissions/${id}/review`,
      expect.objectContaining({ body, method: "POST", headers: expect.objectContaining({ "X-Browser-Session": "browser-session" }) }));
  });

  it("forwards a valid 10,000-character section after JSON escaping", async () => {
    const body = JSON.stringify({ expected_version: 1, section_code: "problem", body: "\u0001".repeat(9999) + "x" });
    const upstream = vi.fn(async () => Response.json({ version: 2 }));
    vi.stubGlobal("fetch", upstream);
    expect((await send(["organizations", org, "enrollments", id, "sections"], body)).status).toBe(200);
    expect(upstream).toHaveBeenCalledOnce();
  });

  it.each([["review", 262144], ["sections", 65536], ["submit", 1024]] as const)("rejects oversized %s payloads before forwarding", async (action, bound) => {
    const upstream = vi.fn();
    vi.stubGlobal("fetch", upstream);
    const body = JSON.stringify({ body: "அ".repeat(Math.ceil(bound / 3)) });
    const path = ["organizations", org, action === "review" ? "submissions" : "enrollments", id, action];
    const response = await send(path, body);
    expect(response.status).toBe(413);
    expect(upstream).not.toHaveBeenCalled();
  });

  it("keeps CSRF and invalid-JSON rejection before forwarding", async () => {
    const upstream = vi.fn();
    vi.stubGlobal("fetch", upstream);
    const path = ["organizations", org, "enrollments", id, "sections"];
    expect((await send(path, "{}", "wrong-token")).status).toBe(403);
    expect((await send(path, "{broken")).status).toBe(400);
    expect(upstream).not.toHaveBeenCalled();
  });
});
