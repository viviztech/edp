import { describe, expect, it } from "vitest";
import { applicationAdminPath } from "./application-admin-security";

const org = "11111111-1111-4111-8111-111111111111";
const form = "22222222-2222-4222-8222-222222222222";

describe("application definition BFF allowlist", () => {
  it("allows only explicit definition administration routes", () => {
    expect(applicationAdminPath(["organizations", org, "definitions"], "GET"))
      .toBe(`/applications/organizations/${org}/definitions`);
    expect(applicationAdminPath(["organizations", org, "definitions", form], "PATCH"))
      .toBe(`/applications/organizations/${org}/definitions/${form}`);
    expect(applicationAdminPath(["organizations", org, "definitions", form, "publish"], "POST"))
      .toBe(`/applications/organizations/${org}/definitions/${form}/publish`);
  });

  it("rejects applicant, malformed, and unsupported routes", () => {
    expect(applicationAdminPath(["organizations", org, "draft"], "GET")).toBeNull();
    expect(applicationAdminPath(["organizations", "bad", "definitions"], "GET")).toBeNull();
    expect(applicationAdminPath(["organizations", org, "definitions", form], "DELETE")).toBeNull();
    expect(applicationAdminPath(["organizations", org, "definitions", form, "publish", "extra"], "POST")).toBeNull();
  });
});
