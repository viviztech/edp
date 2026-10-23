import Link from "next/link";
import { ArrowUpRight, Bell, BookOpen, Building2, ClipboardList, FilePenLine, Handshake, ListChecks, Network, ScanLine, UsersRound } from "lucide-react";
import { attendanceMessages } from "../lib/attendance-messages";
import { applicationAdminMessages } from "../lib/application-admin-messages";
import { authMessages } from "../lib/auth-messages";
import { cmsMessages } from "../lib/cms-messages";
import { crmMessages } from "../lib/crm-messages";
import { metaMessages } from "../lib/meta-messages";
import { mentoringMessages } from "../lib/mentoring-messages";
import { learningMessages } from "../lib/learning-messages";
import { notificationMessages } from "../lib/notification-messages";
import { programMessages } from "../lib/program-messages";
import { selectionMessages } from "../lib/selection-messages";

type ModuleKey = "pages" | "content" | "media" | "enquiries" | "filePolicies" | "crm" | "notifications" | "meta" | "applicationDefinitions" | "programs" | "selection" | "learning" | "attendance" | "mentoring" | "businesses" | "knowledge" | "helpdesk" | "reports";
type Locale = "en" | "ta";

const descriptions: Record<Locale, Record<ModuleKey, string>> = {
  en: {
    pages: "Create and publish program pages.",
    content: "Draft and publish bilingual news, events, answers and stories.",
    media: "Review registered media metadata and recorded scan states.",
    enquiries: "Review public enquiries and manage the next response.",
    filePolicies: "Configure explicit formats, limits, notices and retention by purpose.",
    crm: "Review leads and plan the next action.",
    notifications: "See assignments, due follow-ups and delivery failures.",
    meta: "Monitor lead forms and delivery.",
    applicationDefinitions: "Version the bilingual applicant form policy.",
    programs: "Plan programs, centers, cohorts and intake cycles.",
    selection: "Configure rubrics and assign submitted applications.",
    learning: "Build courses and place them in cohort pathways.",
    attendance: "Open check-in windows and maintain session registers.",
    mentoring: "Match mentors, schedule sessions and track agreed outcomes.",
    businesses: "Review business progress and follow-up reports.",
    knowledge: "Publish support resources and review participant funding progress.",
    helpdesk: "Respond to assigned support tickets and track their resolution.",
    reports: "Review defined measures, preserve snapshots and export authorized evidence.",
  },
  ta: {
    filePolicies: "நோக்கத்தின்படி கோப்பு வடிவங்கள், வரம்புகள், அறிவிப்புகள் மற்றும் காலங்களை அமைக்கவும்.",
    content: "இருமொழிச் செய்திகள், நிகழ்வுகள், பதில்கள் மற்றும் அனுபவங்களை வெளியிடுக.",
    media: "ஊடக விவரங்களையும் பதிவு செய்யப்பட்ட பரிசோதனை நிலைகளையும் பார்க்கவும்.",
    enquiries: "பொது விசாரணைகளைப் பார்த்து அடுத்த பதிலை நிர்வகிக்கவும்.",
    reports: "வரையறுக்கப்பட்ட அளவீடுகளைப் பார்த்து, அறிக்கைச் சான்றுகளைச் சேமிக்கவும்.",
    helpdesk: "ஒதுக்கப்பட்ட உதவிக் கோரிக்கைகளுக்குப் பதிலளித்து தீர்வைக் கண்காணிக்கவும்.",
    pages: "\u0ba4\u0bbf\u0b9f\u0bcd\u0b9f\u0baa\u0bcd \u0baa\u0b95\u0bcd\u0b95\u0b99\u0bcd\u0b95\u0bb3\u0bc8 \u0b89\u0bb0\u0bc1\u0bb5\u0bbe\u0b95\u0bcd\u0b95\u0bbf \u0bb5\u0bc6\u0bb3\u0bbf\u0baf\u0bbf\u0b9f\u0bc1\u0b99\u0bcd\u0b95\u0bb3\u0bcd.",
    crm: "\u0bb5\u0bbe\u0baf\u0bcd\u0baa\u0bcd\u0baa\u0bc1\u0b95\u0bb3\u0bc8\u0baa\u0bcd \u0baa\u0bbe\u0bb0\u0bcd\u0ba4\u0bcd\u0ba4\u0bc1 \u0b85\u0b9f\u0bc1\u0ba4\u0bcd\u0ba4 \u0ba8\u0b9f\u0bb5\u0b9f\u0bbf\u0b95\u0bcd\u0b95\u0bc8\u0baf\u0bc8\u0ba4\u0bcd \u0ba4\u0bbf\u0b9f\u0bcd\u0b9f\u0bae\u0bbf\u0b9f\u0bc1\u0b99\u0bcd\u0b95\u0bb3\u0bcd.",
    notifications: "\u0b92\u0ba4\u0bc1\u0b95\u0bcd\u0b95\u0bc0\u0b9f\u0bc1\u0b95\u0bb3\u0bc8\u0baf\u0bc1\u0bae\u0bcd \u0ba8\u0bbf\u0bb2\u0bc1\u0bb5\u0bc8\u0ba4\u0bcd \u0ba4\u0bca\u0b9f\u0bb0\u0bcd\u0b9a\u0bcd\u0b9a\u0bbf\u0baa\u0bcd \u0baa\u0ba3\u0bbf\u0b95\u0bb3\u0bc8\u0baf\u0bc1\u0bae\u0bcd \u0baa\u0bbe\u0bb0\u0bcd\u0b95\u0bcd\u0b95\u0bb5\u0bc1\u0bae\u0bcd.",
    meta: "\u0bb5\u0bbe\u0baf\u0bcd\u0baa\u0bcd\u0baa\u0bc1 \u0baa\u0b9f\u0bbf\u0bb5\u0b99\u0bcd\u0b95\u0bb3\u0bc8\u0baf\u0bc1\u0bae\u0bcd \u0bb5\u0bb0\u0bb5\u0bc8\u0baf\u0bc1\u0bae\u0bcd \u0b95\u0ba3\u0bcd\u0b95\u0bbe\u0ba3\u0bbf\u0b95\u0bcd\u0b95\u0bb5\u0bc1\u0bae\u0bcd.",
    applicationDefinitions: "\u0b87\u0bb0\u0bc1\u0bae\u0bca\u0bb4\u0bbf \u0bb5\u0bbf\u0ba3\u0bcd\u0ba3\u0baa\u0bcd\u0baa\u0baa\u0bcd \u0baa\u0b9f\u0bbf\u0bb5\u0b95\u0bcd \u0b95\u0bca\u0bb3\u0bcd\u0b95\u0bc8\u0baf\u0bc8\u0baa\u0bcd \u0baa\u0ba4\u0bbf\u0baa\u0bcd\u0baa\u0bc1\u0b95\u0bb3\u0bbe\u0b95 \u0bae\u0bc7\u0bb2\u0bbe\u0ba3\u0bcd\u0bae\u0bc8 \u0b9a\u0bc6\u0baf\u0bcd\u0baf\u0bb5\u0bc1\u0bae\u0bcd.",
    programs: "\u0ba4\u0bbf\u0b9f\u0bcd\u0b9f\u0b99\u0bcd\u0b95\u0bb3\u0bcd, \u0bae\u0bc8\u0baf\u0b99\u0bcd\u0b95\u0bb3\u0bcd, \u0b95\u0bc1\u0bb4\u0bc1\u0b95\u0bcd\u0b95\u0bb3\u0bcd \u0bae\u0bb1\u0bcd\u0bb1\u0bc1\u0bae\u0bcd \u0bb5\u0bbf\u0ba3\u0bcd\u0ba3\u0baa\u0bcd\u0baa\u0b95\u0bcd \u0b95\u0bbe\u0bb2\u0b99\u0bcd\u0b95\u0bb3\u0bc8\u0ba4\u0bcd \u0ba4\u0bbf\u0b9f\u0bcd\u0b9f\u0bae\u0bbf\u0b9f\u0bc1\u0b99\u0bcd\u0b95\u0bb3\u0bcd.",
    selection: "மதிப்பீட்டுப் பட்டியலை அமைத்து விண்ணப்பங்களை ஒதுக்கவும்.",
    learning: "\u0baa\u0bbe\u0b9f\u0ba8\u0bc6\u0bb1\u0bbf\u0b95\u0bb3\u0bc8 \u0b89\u0bb0\u0bc1\u0bb5\u0bbe\u0b95\u0bcd\u0b95\u0bbf \u0b95\u0bc1\u0bb4\u0bc1 \u0baa\u0bbe\u0ba4\u0bc8\u0b95\u0bb3\u0bbf\u0bb2\u0bcd \u0bb5\u0bc8\u0b95\u0bcd\u0b95\u0bb5\u0bc1\u0bae\u0bcd.",
    attendance: "\u0b85\u0bae\u0bb0\u0bcd\u0bb5\u0bc1 \u0bb5\u0bb0\u0bc1\u0b95\u0bc8\u0baf\u0bc8 \u0ba4\u0bbf\u0bb1\u0ba8\u0bcd\u0ba4\u0bc1 \u0baa\u0ba4\u0bbf\u0bb5\u0bc7\u0b9f\u0bc1\u0b95\u0bb3\u0bc8 \u0ba8\u0bbf\u0bb0\u0bcd\u0bb5\u0b95\u0bbf\u0b95\u0bcd\u0b95\u0bb5\u0bc1\u0bae\u0bcd.",
    mentoring: "\u0bb5\u0bb4\u0bbf\u0b95\u0bbe\u0b9f\u0bcd\u0b9f\u0bbf\u0b95\u0bb3\u0bc8 \u0b92\u0ba4\u0bc1\u0b95\u0bcd\u0b95\u0bbf \u0b85\u0bae\u0bb0\u0bcd\u0bb5\u0bc1\u0b95\u0bb3\u0bc8\u0ba4\u0bcd \u0ba4\u0bbf\u0b9f\u0bcd\u0b9f\u0bae\u0bbf\u0b9f\u0bb5\u0bc1\u0bae\u0bcd.",
    businesses: "தொழில் முன்னேற்றம் மற்றும் பின்தொடர்வு அறிக்கைகளைப் பார்க்கவும்.",
    knowledge: "ஆதரவு வளங்களை வெளியிட்டு நிதி முன்னேற்றத்தைப் பார்க்கவும்.",
  },
};

const modules = [
  { key: "pages", route: "pages", permission: "cms.page.view", Icon: FilePenLine },
  { key: "content", route: "content", permission: "cms.editorial.view", Icon: FilePenLine },
  { key: "media", route: "media", permission: "cms.asset.view", Icon: BookOpen },
  { key: "enquiries", route: "enquiries", permission: "enquiry.view", Icon: ClipboardList },
  { key: "filePolicies", route: "file-policies", permission: "files.policy.view", Icon: ClipboardList },
  { key: "crm", route: "crm", permission: "crm.lead.view", Icon: UsersRound },
  { key: "notifications", route: "notifications", permission: "crm.lead.view", Icon: Bell },
  { key: "meta", route: "meta", permission: "meta.integration.view", Icon: Network },
  { key: "applicationDefinitions", route: "application-definitions", permission: "application.form.view", Icon: ClipboardList },
  { key: "programs", route: "programs", permission: "program.view", Icon: Building2 },
  { key: "selection", route: "selection", permission: "selection.cycle.view", Icon: ListChecks },
  { key: "learning", route: "learning", permission: "lms.course.view", Icon: BookOpen },
  { key: "attendance", route: "attendance", permission: "attendance.view", Icon: ScanLine },
  { key: "mentoring", route: "mentoring", permission: "mentoring.view", Icon: Handshake },
  { key: "businesses", route: "businesses", permission: "business.track.view", Icon: Building2 },
  { key: "knowledge", route: "knowledge", permission: "knowledge.manage", Icon: BookOpen },
  { key: "helpdesk", route: "helpdesk", permission: "ticket.view", Icon: Handshake },
  { key: "reports", route: "reports", permission: "report.view", Icon: ListChecks },
] as const;

export function StaffModuleNav({ locale, organization, permissions, variant = "tabs", active }: {
  locale: Locale;
  organization: string;
  permissions: string[];
  variant?: "tabs" | "tiles";
  active?: ModuleKey;
}) {
  const labels: Record<ModuleKey, string> = {
    filePolicies: locale === "ta" ? "கோப்புக் கொள்கைகள்" : "File policies",
    pages: cmsMessages[locale].workspace,
    content: locale === "ta" ? "உள்ளடக்கப் பகுதி" : "Content studio",
    media: locale === "ta" ? "ஊடக விவரங்கள்" : "Media metadata",
    enquiries: locale === "ta" ? "விசாரணைப் பெட்டி" : "Enquiry inbox",
    crm: crmMessages[locale].workspace,
    notifications: notificationMessages[locale].workspace,
    meta: metaMessages[locale].workspace,
    applicationDefinitions: applicationAdminMessages[locale].workspace,
    programs: programMessages[locale].workspace,
    selection: selectionMessages[locale].workspace,
    learning: learningMessages[locale].workspace,
    attendance: attendanceMessages[locale].workspace,
    mentoring: mentoringMessages[locale].workspace,
    businesses: locale === "ta" ? "தொழில் பின்தொடர்வு" : "Business tracking",
    knowledge: locale === "ta" ? "வளங்கள் மற்றும் நிதி" : "Resources and funding",
    helpdesk: locale === "ta" ? "உதவி மையம்" : "Helpdesk",
    reports: locale === "ta" ? "அறிக்கைகள் மற்றும் தாக்கம்" : "Reports and impact",
  };
  const available = modules.filter((module) =>
    permissions.includes(module.permission)
    || (module.key === "learning" && permissions.includes("lms.delivery.view"))
    || (module.key === "notifications" && permissions.includes("notification.operations.view"))
    || (module.key === "knowledge" && permissions.includes("funding.manage"))
    || (module.key === "reports" && permissions.includes("impact.manage"))
  );
  if (available.length === 0) return null;
  return <nav className={"staff-modules staff-modules-" + variant} aria-label={authMessages[locale].staff}>
    {available.map(({ key, route, Icon }) => <Link
      key={key}
      className="staff-module"
      href={`/${locale}/admin/${route}?organization=${organization}`}
      aria-current={active === key ? "page" : undefined}
    >
      <span className="staff-module-icon" aria-hidden="true"><Icon size={22} strokeWidth={1.7} /></span>
      <span className="staff-module-copy"><strong>{labels[key]}</strong>{variant === "tiles" && <small>{descriptions[locale][key]}</small>}</span>
      {variant === "tiles" && <ArrowUpRight className="staff-module-arrow" size={20} aria-hidden="true" />}
    </Link>)}
  </nav>;
}
