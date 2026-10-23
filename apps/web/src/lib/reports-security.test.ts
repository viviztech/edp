import { describe, expect, it } from "vitest";
import { reportsPath, reportQuery } from "./reports-security";
import { impactPath, impactQuery } from "./impact-security";

const org = "11111111-1111-4111-8111-111111111111"; const item = "22222222-2222-4222-8222-222222222222";
describe("report and impact route boundaries", () => {
  it("permits only fixed organization paths and methods including bound download capabilities", () => {
    expect(reportsPath(["organizations", org, "dashboard"], "GET")).toBe(`/reports/organizations/${org}/dashboard`);
    expect(reportsPath(["organizations", org, "exports", item, "download", "a".repeat(43)], "GET")).toContain("/download/");
    for (const path of [["..", "auth"], ["organizations", org, "exports", item, "download", "https://example.com"], ["organizations", org, "raw-participants"]]) expect(reportsPath(path, "GET")).toBeNull();
    expect(reportsPath(["organizations", org, "dashboard"], "POST")).toBeNull();
    expect(impactPath(["organizations", org, "records"], "POST")).toBe(`/impact/organizations/${org}/records`);
    expect(impactPath(["organizations", org, "definitions", item, "publish"], "POST")).toContain("/publish");
    expect(impactPath(["organizations", org, "records", item], "PATCH")).toBeNull();
  });
  it("accepts unique bounded normalized filters and denies unknown or malformed query values", () => {
    expect(reportQuery(new URLSearchParams(`from_date=2026-01-01&through_date=2026-10-21&program_id=${org}&limit=25`))).toContain("from_date=2026-01-01");
    for (const query of ["from_date=2026-02-30", "from_date=2026-01-01&from_date=2026-01-02", "token=private", "limit=101", "cursor=abc", "locale=en"]) expect(reportQuery(new URLSearchParams(query))).toBeNull();
    expect(impactQuery(new URLSearchParams(`enrollment_id=${item}&stage=baseline&observed_on=2026-10-01&limit=100`))).toContain("stage=baseline");
    for (const query of ["stage=made-up", "state=draft&state=published", "observed_on=2026-02-31", "participant_id=" + org]) expect(impactQuery(new URLSearchParams(query))).toBeNull();
  });
});
