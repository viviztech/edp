import { describe, expect, it } from "vitest";
import { hasStaffWorkspaceAccess } from "./account-access";
describe("file-policy account destination", () => {
  it("requires both system access and a real view capability", () => {
    expect(hasStaffWorkspaceAccess(["system.access", "files.policy.view"])).toBe(true);
    expect(hasStaffWorkspaceAccess(["files.policy.view"])).toBe(false);
    expect(hasStaffWorkspaceAccess(["system.access", "files.policy.manage"])).toBe(false);
  });
});
