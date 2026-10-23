const staffPermissions = new Set([
  "audit.view", "cms.page.view", "cms.editorial.view", "cms.asset.view", "enquiry.view", "files.policy.view", "crm.lead.view", "notification.operations.view",
  "meta.integration.view", "application.form.view", "program.view", "selection.cycle.view",
  "lms.course.view", "lms.delivery.view", "attendance.view", "mentoring.view",
  "business.track.view", "knowledge.manage", "funding.manage", "ticket.view", "report.view", "impact.manage",
]);

export function hasStaffWorkspaceAccess(permissions: string[]): boolean {
  return permissions.includes("system.access") && permissions.some(permission => staffPermissions.has(permission));
}
