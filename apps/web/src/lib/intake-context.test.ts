import { describe, expect, it } from "vitest";
import { accountHref, applicationHref, readIntakeContext } from "./intake-context";
import { hasStaffWorkspaceAccess } from "./account-access";

const organization = "AAAAAAAA-1111-4111-8111-111111111111";
const cycle = "bbbbbbbb-2222-4222-8222-222222222222";

describe("intake account context", () => {
  it("preserves only validated intake identifiers on known locale routes", () => {
    const context = readIntakeContext({ organization, cycle, returnTo: "https://example.com/" });
    expect(context).toEqual({ organization: organization.toLowerCase(), cycle });
    expect(accountHref("ta", context)).toBe(`/ta/account?organization=${organization.toLowerCase()}&cycle=${cycle}`);
    expect(applicationHref("ta", context)).toBe(`/ta/applications?organization=${organization.toLowerCase()}&cycle=${cycle}`);
  });

  it("supports ordinary applicants through the configured public organization", () => {
    expect(readIntakeContext({}, organization)).toEqual({ organization: organization.toLowerCase() });
    expect(applicationHref("en")).toBe("/en/applications");
  });

  it.each(["https://example.com", "//example.com", "../admin", "/ta/admin", "%2f%2fexample.com", "11111111-1111-1111-1111-11111111111z", [organization, organization]])("rejects invalid or repeated organizations: %s", value => {
    expect(readIntakeContext({ organization: value, cycle }, organization)).toEqual({});
  });

  it("discards malformed/repeated or unscoped cycles and validates callers again", () => {
    expect(readIntakeContext({ cycle })).toEqual({});
    expect(readIntakeContext({ organization, cycle: [cycle, cycle] })).toEqual({ organization: organization.toLowerCase() });
    expect(applicationHref("en", { organization: "//example.com", cycle })).toBe("/en/applications");
  });
});

describe("account workspace destinations", () => {
  it("does not treat baseline system access or participant permissions as staff capabilities", () => {
    expect(hasStaffWorkspaceAccess(["system.access", "participant.self", "lms.learn"])).toBe(false);
    expect(hasStaffWorkspaceAccess(["crm.lead.view"])).toBe(false);
    expect(hasStaffWorkspaceAccess(["system.access", "crm.lead.view"])).toBe(true);
    expect(hasStaffWorkspaceAccess(["system.access", "enquiry.view"])).toBe(true);
    expect(hasStaffWorkspaceAccess(["system.access", "cms.editorial.view"])).toBe(true);
    expect(hasStaffWorkspaceAccess(["system.access", "cms.asset.view"])).toBe(true);
  });
});
