import { describe, expect, it } from "vitest";
import { crmExportQuery, crmPath } from "./crm-security";

const id = "11111111-1111-4111-8111-111111111111";

describe("crmPath", () => {
  it("allows the explicit CRM workflow routes", () => {
    expect(crmPath(["organizations", id, "leads"], "GET")).toBe(`/crm/organizations/${id}/leads`);
    expect(crmPath(["organizations", id, "leads", id, "activities"], "POST")).toContain("/crm/");
    expect(crmPath(["organizations", id, "duplicate-reviews", id, "resolve"], "POST")).toContain("/crm/");
    expect(crmPath(["organizations", id, "exports", id, "download"], "GET")).toContain("/crm/");
    expect(crmPath(["organizations", id, "exports"], "GET")).toBe(`/crm/organizations/${id}/exports`);
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

describe("CRM export query boundaries", () => {
  it("passes only bounded unique history pagination", () => {
    expect(crmExportQuery(new URLSearchParams(), true)?.toString()).toBe("limit=25");
    expect(crmExportQuery(new URLSearchParams({ cursor: id, limit: "100" }), true)?.get("cursor")).toBe(id);
    for (const value of ["limit=0", "limit=101", "limit=1&limit=2", "cursor=invalid", `cursor=${id}&cursor=${id}`, "requested_by_id=" + id, "organization=" + id]) {
      expect(crmExportQuery(new URLSearchParams(value), true)).toBeNull();
    }
  });

  it("rejects queries for detail, download and mutation routes", () => {
    expect(crmExportQuery(new URLSearchParams(), false)?.size).toBe(0);
    expect(crmExportQuery(new URLSearchParams({ cursor: id }), false)).toBeNull();
    expect(crmExportQuery(new URLSearchParams({ limit: "25" }), false)).toBeNull();
  });
});
