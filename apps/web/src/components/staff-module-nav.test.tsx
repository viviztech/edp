import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { StaffModuleNav } from "./staff-module-nav";
import { applicationAdminMessages } from "../lib/application-admin-messages";
import { cmsMessages } from "../lib/cms-messages";
import { crmMessages } from "../lib/crm-messages";
import { metaMessages } from "../lib/meta-messages";

afterEach(cleanup);

describe("staff module navigation", () => {
  it("links only to modules granted for the selected organization", () => {
    render(<StaffModuleNav locale="en" organization="org-1" permissions={["cms.page.view", "crm.lead.view"]} variant="tiles" />);
    expect(screen.getByText(cmsMessages.en.workspace).closest("a")?.getAttribute("href")).toBe("/en/admin/pages?organization=org-1");
    expect(screen.queryByText(metaMessages.en.workspace)).toBeNull();
    expect(screen.getAllByRole("link")).toHaveLength(3);
  });

  it("keeps CRM Tamil labels readable", () => {
    expect(Object.values(crmMessages.ta).some((value) => /\?{3,}/.test(value))).toBe(false);
  });

  it("marks the active module without adding an ungranted link", () => {
    render(<StaffModuleNav locale="ta" organization="org-2" permissions={["meta.integration.view"]} active="meta" />);
    const link = screen.getByRole("link");
    expect(link.getAttribute("href")).toBe("/ta/admin/meta?organization=org-2");
    expect(link.getAttribute("aria-current")).toBe("page");
  });

  it("links application policy only for its scoped view permission", () => {
    render(<StaffModuleNav locale="en" organization="org-3" permissions={["application.form.view"]} variant="tiles" />);
    const link = screen.getByText(applicationAdminMessages.en.workspace).closest("a");
    expect(link?.getAttribute("href")).toBe("/en/admin/application-definitions?organization=org-3");
    expect(screen.getAllByRole("link")).toHaveLength(1);
  });
});
