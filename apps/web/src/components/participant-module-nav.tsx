import Link from "next/link";
import type { Locale } from "../lib/messages";

const modules = [
  { route: "updates", en: "My updates", ta: "எனது அறிவிப்புகள்", permission: "participant.self" },
  { route: "participant", en: "My schedule", ta: "எனது அட்டவணை", permission: "participant.self" },
  { route: "learning", en: "My learning", ta: "எனது கற்றல்", permission: "lms.learn" },
  { route: "attendance", en: "My attendance", ta: "எனது வருகை", permission: "participant.self" },
  { route: "mentoring", en: "My mentoring", ta: "எனது வழிகாட்டுதல்", permission: "participant.self" },
  { route: "business-plan", en: "My business plan", ta: "எனது வணிகத் திட்டம்", permission: "participant.self" },
  { route: "businesses", en: "My business", ta: "எனது தொழில்", permission: "participant.self" },
  { route: "knowledge", en: "Resources and funding", ta: "வளங்கள் மற்றும் நிதி", permission: "participant.self" },
  { route: "helpdesk", en: "Helpdesk", ta: "உதவி மையம்", permission: "participant.self" },
  { route: "impact", en: "My business outcomes", ta: "எனது தொழில் விளைவுகள்", permission: "participant.self" },
] as const;

export type ParticipantModule = typeof modules[number]["route"];

export function ParticipantModuleNav({ locale, organization, permissions, active }: {
  locale: Locale;
  organization: string;
  permissions: string[];
  active?: ParticipantModule;
}) {
  const available = modules.filter(module => permissions.includes(module.permission));
  if (!available.length) return null;
  return <nav className="participant-modules actions" aria-label={locale === "ta" ? "பங்கேற்பாளர் வழிசெலுத்தல்" : "Participant navigation"}>
    {available.map(module => <Link key={module.route}
      href={`/${locale}/${module.route}?${new URLSearchParams({ organization })}`}
      aria-current={active === module.route ? "page" : undefined}>{module[locale]}</Link>)}
    <Link href={`/${locale}/account`}>{locale === "ta" ? "எனது கணக்கு" : "My account"}</Link>
  </nav>;
}
