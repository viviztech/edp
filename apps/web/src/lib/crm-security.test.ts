import { describe, expect, it } from "vitest";
import { crmPath } from "./crm-security";

const id = "11111111-1111-4111-8111-111111111111";

describe("crmPath", () => {
  it("allows the explicit CRM workflow routes", () => {
    expect(crmPath(["organizations", id, "leads"], "GET")).toBe(`/crm/organizations/${id}/leads`);
    expect(crmPath(["organizations", id, "leads", id, "activities"], "POST")).toContain("/crm/");
    expect(crmPath(["organizations", id, "duplicate-reviews", id, "resolve"], "POST")).toContain("/crm/");
    expect(crmPath(["organizations", id, "exports", id, "download"], "GET")).toContain("/crm/");
    expect(crmPath(["organizations", id, "tags"], "GET")).toContain("/crm/");
    expect(crmPath(["organizations", id, "leads", id, "tags", id, "attach"], "POST")).toContain("/crm/");
    expect(crmPath(["organizations", id, "leads", id, "activities", id, "complete"], "POST")).toContain("/crm/");
  });

  it("rejects arbitrary upstream paths and methods", () => {
    expect(crmPath(["organizations", id, "leads", "..", "auth"], "GET")).toBeNull();
    expect(crmPath(["organizations", id, "exports", id, "download"], "POST")).toBeNull();
    expect(crmPath(["organizations", id, "leads"], "DELETE")).toBeNull();
  });
});
