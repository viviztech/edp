import { describe, expect, it } from "vitest";
import { enquiryPath, enquiryQuery, safePrivacyUrl } from "./enquiry-security";
const org = "11111111-1111-4111-8111-111111111111", id = "22222222-2222-4222-8222-222222222222";
const queue = `/cms/organizations/${org}/enquiries/queue`;
describe("closed enquiry transport", () => {
  it("permits only supported staff reads and versioned status commands", () => {
    expect(enquiryPath(["organizations", org, "enquiries", "queue"], "GET")).toBe(queue);
    expect(enquiryPath(["organizations", org, "enquiries", id, "status"], "POST")).toBe(`/cms/organizations/${org}/enquiries/${id}/status`);
    for (const path of [["organizations", org, "enquiries"], ["organizations", org, "enquiries", id, "notes"], ["organizations", org, "enquiries", "..", "auth"]]) expect(enquiryPath(path, "POST")).toBeNull();
    expect(enquiryPath(["organizations", org, "enquiries", id], "DELETE")).toBeNull();
  });
  it("bounds queue filters and prevents query drift into detail or mutations", () => {
    expect(enquiryQuery(new URLSearchParams(`limit=25&cursor=${id}&status=reviewed`), queue, "GET")).toBe(`limit=25&cursor=${id}&status=reviewed`);
    for (const query of ["status=closed&status=new", "limit=101", "token=secret", "cursor=../../auth", "status=archived"]) expect(enquiryQuery(new URLSearchParams(query), queue, "GET")).toBeNull();
    expect(enquiryQuery(new URLSearchParams("limit=1"), queue.replace("queue", id), "GET")).toBeNull();
    expect(enquiryQuery(new URLSearchParams("status=new"), queue, "POST")).toBeNull();
  });
  it("accepts configured document links and excludes executable or credential-bearing links", () => {
    expect(safePrivacyUrl("/ta/pages/privacy-notice")).toBe(true);
    expect(safePrivacyUrl("https://example.test/privacy")).toBe(true);
    for (const value of ["//evil.test", "javascript:alert(1)", "https://user:pass@example.test", "/en/pages/../account", "http://example.test/privacy"]) expect(safePrivacyUrl(value)).toBe(false);
  });
});
