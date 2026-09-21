import Link from "next/link";
import { ArrowUpRight, Bell, FilePenLine, Network, UsersRound } from "lucide-react";
import { cmsMessages } from "../lib/cms-messages";
import { crmMessages } from "../lib/crm-messages";
import { metaMessages } from "../lib/meta-messages";
import { notificationMessages } from "../lib/notification-messages";
import { authMessages } from "../lib/auth-messages";

type ModuleKey = "pages" | "crm" | "notifications" | "meta";
type Locale = "en" | "ta";

const descriptions: Record<Locale, Record<ModuleKey, string>> = {
  en: {
    pages: "Create and publish program pages.",
    crm: "Review leads and plan the next action.",
    notifications: "See assignments and due follow-ups.",
    meta: "Monitor lead forms and delivery.",
  },
  ta: {
    pages: "\u0ba4\u0bbf\u0b9f\u0bcd\u0b9f\u0baa\u0bcd \u0baa\u0b95\u0bcd\u0b95\u0b99\u0bcd\u0b95\u0bb3\u0bc8 \u0b89\u0bb0\u0bc1\u0bb5\u0bbe\u0b95\u0bcd\u0b95\u0bbf \u0bb5\u0bc6\u0bb3\u0bbf\u0baf\u0bbf\u0b9f\u0bc1\u0b99\u0bcd\u0b95\u0bb3\u0bcd.",
    crm: "\u0bb5\u0bbe\u0baf\u0bcd\u0baa\u0bcd\u0baa\u0bc1\u0b95\u0bb3\u0bc8\u0baa\u0bcd \u0baa\u0bbe\u0bb0\u0bcd\u0ba4\u0bcd\u0ba4\u0bc1 \u0b85\u0b9f\u0bc1\u0ba4\u0bcd\u0ba4 \u0ba8\u0b9f\u0bb5\u0b9f\u0bbf\u0b95\u0bcd\u0b95\u0bc8\u0baf\u0bc8\u0ba4\u0bcd \u0ba4\u0bbf\u0b9f\u0bcd\u0b9f\u0bae\u0bbf\u0b9f\u0bc1\u0b99\u0bcd\u0b95\u0bb3\u0bcd.",
    notifications: "\u0b92\u0ba4\u0bc1\u0b95\u0bcd\u0b95\u0bc0\u0b9f\u0bc1\u0b95\u0bb3\u0bc8\u0baf\u0bc1\u0bae\u0bcd \u0ba8\u0bbf\u0bb2\u0bc1\u0bb5\u0bc8\u0ba4\u0bcd \u0ba4\u0bca\u0b9f\u0bb0\u0bcd\u0b9a\u0bcd\u0b9a\u0bbf\u0baa\u0bcd \u0baa\u0ba3\u0bbf\u0b95\u0bb3\u0bc8\u0baf\u0bc1\u0bae\u0bcd \u0baa\u0bbe\u0bb0\u0bcd\u0b95\u0bcd\u0b95\u0bb5\u0bc1\u0bae\u0bcd.",
    meta: "\u0bb5\u0bbe\u0baf\u0bcd\u0baa\u0bcd\u0baa\u0bc1 \u0baa\u0b9f\u0bbf\u0bb5\u0b99\u0bcd\u0b95\u0bb3\u0bc8\u0baf\u0bc1\u0bae\u0bcd \u0bb5\u0bb0\u0bb5\u0bc8\u0baf\u0bc1\u0bae\u0bcd \u0b95\u0ba3\u0bcd\u0b95\u0bbe\u0ba3\u0bbf\u0b95\u0bcd\u0b95\u0bb5\u0bc1\u0bae\u0bcd.",
  },
};

const modules = [
  { key: "pages", permission: "cms.page.view", Icon: FilePenLine },
  { key: "crm", permission: "crm.lead.view", Icon: UsersRound },
  { key: "notifications", permission: "crm.lead.view", Icon: Bell },
  { key: "meta", permission: "meta.integration.view", Icon: Network },
] as const;

export function StaffModuleNav({
  locale, organization, permissions, variant = "tabs", active,
}: {
  locale: Locale;
  organization: string;
  permissions: string[];
  variant?: "tabs" | "tiles";
  active?: ModuleKey;
}) {
  const labels: Record<ModuleKey, string> = {
    pages: cmsMessages[locale].workspace,
    crm: crmMessages[locale].workspace,
    notifications: notificationMessages[locale].workspace,
    meta: metaMessages[locale].workspace,
  };
  const available = modules.filter((module) => permissions.includes(module.permission));
  if (available.length === 0) return null;
  return <nav className={"staff-modules staff-modules-" + variant} aria-label={authMessages[locale].staff}>
    {available.map(({ key, Icon }) => <Link
      key={key}
      className="staff-module"
      href={`/${locale}/admin/${key}?organization=${organization}`}
      aria-current={active === key ? "page" : undefined}
    >
      <span className="staff-module-icon" aria-hidden="true"><Icon size={22} strokeWidth={1.7} /></span>
      <span className="staff-module-copy"><strong>{labels[key]}</strong>{variant === "tiles" && <small>{descriptions[locale][key]}</small>}</span>
      {variant === "tiles" && <ArrowUpRight className="staff-module-arrow" size={20} aria-hidden="true" />}
    </Link>)}
  </nav>;
}
