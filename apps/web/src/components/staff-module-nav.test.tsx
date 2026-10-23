import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { StaffModuleNav } from "./staff-module-nav";
import { applicationAdminMessages } from "../lib/application-admin-messages";
import { cmsMessages } from "../lib/cms-messages";
import { crmMessages } from "../lib/crm-messages";
import { metaMessages } from "../lib/meta-messages";
import { programMessages } from "../lib/program-messages";

afterEach(cleanup);

describe("staff module navigation", () => {
  it("exposes editorial and media only for their respective scoped view rights", () => {
    const view = render(<StaffModuleNav locale="en" organization="org-content" permissions={["cms.editorial.view"]} active="content" />);
    expect(screen.getByRole("link", { name: "Content studio" }).getAttribute("href")).toBe("/en/admin/content?organization=org-content");
    expect(screen.queryByRole("link", { name: "Media metadata" })).toBeNull();
    view.rerender(<StaffModuleNav locale="ta" organization="org-media" permissions={["cms.asset.view"]} active="media" />);
    expect(screen.getByRole("link", { name: "ஊடக விவரங்கள்" }).getAttribute("href")).toBe("/ta/admin/media?organization=org-media");
    expect(screen.getAllByRole("link")).toHaveLength(1);
    view.rerender(<StaffModuleNav locale="en" organization="org-content" permissions={["cms.editorial.create", "cms.asset.publish"]} />);
    expect(screen.queryByRole("navigation")).toBeNull();
  });
  it("links the bilingual enquiry inbox only with scoped enquiry access", () => {
    const view = render(<StaffModuleNav locale="ta" organization="org-enquiry" permissions={["enquiry.view"]} active="enquiries" />);
    const link = screen.getByRole("link", { name: "விசாரணைப் பெட்டி" });
    expect(link.getAttribute("href")).toBe("/ta/admin/enquiries?organization=org-enquiry");
    expect(link.getAttribute("aria-current")).toBe("page");
    view.rerender(<StaffModuleNav locale="en" organization="org-enquiry" permissions={["system.access"]} />);
    expect(screen.queryByRole("link", { name: "Enquiry inbox" })).toBeNull();
  });

  it("renders readable Tamil selection guidance", () => {
    render(<StaffModuleNav locale="ta" organization="org-selection" permissions={["selection.cycle.view"]} variant="tiles" />);
    expect(screen.getByText("மதிப்பீட்டுப் பட்டியலை அமைத்து விண்ணப்பங்களை ஒதுக்கவும்.")).toBeTruthy();
    expect(screen.getByRole("navigation").textContent).not.toMatch(/\?{3,}|à®|Ã/);
  });
  it.each(["report.view", "impact.manage"])("links reporting only for scoped %s access", (permission) => {
    render(<StaffModuleNav locale="en" organization="org-report" permissions={[permission]} active="reports" />);
    const link = screen.getByRole("link", { name: "Reports and impact" });
    expect(link.getAttribute("href")).toBe("/en/admin/reports?organization=org-report");
    expect(link.getAttribute("aria-current")).toBe("page");
    expect(screen.getAllByRole("link")).toHaveLength(1);
  });
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
  it("links program administration only with program view permission", () => {
    render(<StaffModuleNav locale="en" organization="org-4" permissions={["program.view"]} variant="tiles" />);
    const link = screen.getByText(programMessages.en.workspace).closest("a");
    expect(link?.getAttribute("href")).toBe("/en/admin/programs?organization=org-4");
    expect(screen.getAllByRole("link")).toHaveLength(1);
  });
  it.each(["knowledge.manage", "funding.manage"])("links knowledge for scoped %s access", (permission) => {
    render(<StaffModuleNav locale="en" organization="org-5" permissions={[permission]} active="knowledge" />);
    const link = screen.getByRole("link", { name: "Resources and funding" });
    expect(link.getAttribute("href")).toBe("/en/admin/knowledge?organization=org-5");
    expect(link.getAttribute("aria-current")).toBe("page");
    expect(screen.getAllByRole("link")).toHaveLength(1);
  });
  it("links the helpdesk only with scoped ticket access", () => {
    const view = render(<StaffModuleNav locale="en" organization="org-6" permissions={["ticket.view"]} active="helpdesk" />);
    const link = screen.getByRole("link", { name: "Helpdesk" });
    expect(link.getAttribute("href")).toBe("/en/admin/helpdesk?organization=org-6");
    expect(link.getAttribute("aria-current")).toBe("page");
    expect(screen.getAllByRole("link")).toHaveLength(1);
    view.rerender(<StaffModuleNav locale="en" organization="org-6" permissions={["system.access"]} />);
    expect(screen.queryByRole("link", { name: "Helpdesk" })).toBeNull();
  });
});
