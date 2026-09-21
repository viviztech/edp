import Link from "next/link";
import { StaffModuleNav } from "../../../../components/staff-module-nav";
import { notFound, redirect } from "next/navigation";
import type { components } from "../../../../lib/api-contracts";
import { isLocale } from "../../../../lib/messages";
import { notificationMessages } from "../../../../lib/notification-messages";
import { serverApi } from "../../../../lib/server-api";
import NotificationWorkspace from "./view";

export const metadata = { robots: { index: false, follow: false } };
export default async function NotificationsPage({ params, searchParams }: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ organization?: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const text = notificationMessages[locale];
  let response: Response;
  try { response = await serverApi("/auth/me"); }
  catch { return <main id="main"><p role="alert">{text.error}</p></main>; }
  if (response.status === 401) redirect(`/${locale}/account`);
  if (!response.ok) return <main id="main"><p role="alert">{text.error}</p></main>;
  const profile: components["schemas"]["Profile"] = await response.json();
  const requested = (await searchParams).organization;
  const grants = profile.grants.filter((item) => item.permissions.includes("crm.lead.view"));
  const grant = grants.find((item) => !requested || item.organization_id === requested);
  if (!grant) return <main id="main"><p>{text.permission}</p><Link href={`/${locale}/admin`}>{text.back}</Link></main>;
  return <main id="main" className="notice-main">
    <div className="notice-heading"><div><p className="eyebrow">{grant.organization_name}</p><h1>{text.workspace}</h1><p>{text.description}</p></div><Link href={`/${locale}/admin?organization=${grant.organization_id}`}>{text.back}</Link></div>
    <StaffModuleNav locale={locale} organization={grant.organization_id} permissions={grant.permissions} active="notifications" />
    {grants.length > 1 ? <nav className="crm-orgs" aria-label={text.workspace}>{grants.map((item) => <a key={item.organization_id} href={`?organization=${item.organization_id}`}>{item.organization_name}</a>)}</nav> : null}
    <NotificationWorkspace key={grant.organization_id} org={grant.organization_id} locale={locale} />
  </main>;
}
