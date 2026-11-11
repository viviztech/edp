import Link from "next/link";
import { BookOpen, BriefcaseBusiness, CalendarDays, ClipboardCheck, FileText, Handshake, UserRound } from "lucide-react";
import { publicLaunch } from "../lib/public-launch";
import "./participant-workspace.css";

type Locale = "en" | "ta";
type Workspace = "applications" | "participant" | "learning" | "attendance" | "mentoring" | "business-plan" | "businesses";

const links = [
  { key: "applications", en: "Application", ta: "விண்ணப்பம்", Icon: FileText },
  { key: "participant", en: "My program", ta: "எனது திட்டம்", Icon: CalendarDays, permission: "participant.self" },
  { key: "learning", en: "Learning", ta: "கற்றல்", Icon: BookOpen, permission: "lms.learn" },
  { key: "attendance", en: "Attendance", ta: "வருகை", Icon: ClipboardCheck, permission: "participant.self" },
  { key: "mentoring", en: "Mentoring", ta: "வழிகாட்டுதல்", Icon: Handshake, permission: "participant.self" },
  { key: "business-plan", en: "Business plan", ta: "வணிகத் திட்டம்", Icon: FileText, permission: "participant.self" },
  { key: "businesses", en: "My business", ta: "எனது தொழில்", Icon: BriefcaseBusiness, permission: "participant.self" },
] as const;

export function ParticipantNavigation({ locale, organization, permissions, active }: {
  locale: Locale;
  organization: string;
  permissions: string[];
  active: Workspace;
}) {
  const applicationEnabled = publicLaunch().selfService;
  return <nav className="participant-navigation" aria-label={locale === "ta" ? "பங்கேற்பாளர் வழிசெலுத்தல்" : "Participant navigation"}>
    <div className="participant-navigation-links">
      {links.filter((item) => (item.key !== "applications" || applicationEnabled) && (!("permission" in item) || permissions.includes(item.permission))).map(({ key, Icon, ...item }) =>
        <Link key={key} href={`/${locale}/${key}?organization=${encodeURIComponent(organization)}`} aria-current={active === key ? "page" : undefined}>
          <Icon size={17} aria-hidden="true" />{item[locale]}
        </Link>)}
      <Link href={`/${locale}/account`}><UserRound size={17} aria-hidden="true" />{locale === "ta" ? "எனது கணக்கு" : "My account"}</Link>
    </div>
  </nav>;
}
