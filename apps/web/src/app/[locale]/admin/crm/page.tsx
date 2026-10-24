import Link from "next/link";
import { StaffModuleNav } from "../../../../components/staff-module-nav";
import { notFound, redirect } from "next/navigation";
import type { components } from "../../../../lib/api-contracts";
import { crmMessages } from "../../../../lib/crm-messages";
import { isLocale } from "../../../../lib/messages";
import { serverApi } from "../../../../lib/server-api";
import CrmWorkspace from "./view";

export const metadata = { robots: { index: false, follow: false } };
export default async function CrmPage({ params, searchParams }: { params: Promise<{ locale: string }>; searchParams: Promise<{ organization?: string }> }) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const text = crmMessages[locale];
  let response: Response;
  try { response = await serverApi("/auth/me"); } catch { return <main id="main" tabIndex={-1}><p role="alert">{text.error}</p></main>; }
  if (response.status === 401) redirect(`/${locale}/account`);
  if (!response.ok) return <main id="main" tabIndex={-1}><p role="alert">{text.error}</p></main>;
  const profile: components["schemas"]["Profile"] = await response.json();
  const requested = (await searchParams).organization;
  const grants = profile.grants.filter((grant) => grant.permissions.includes("crm.lead.view"));
  const grant = grants.find((item) => !requested || item.organization_id === requested);
  if (!grant) return <main id="main" tabIndex={-1}><p>{text.permission}</p><Link href={`/${locale}/admin`}>{text.back}</Link></main>;
  return <main id="main" tabIndex={-1} className="crm-main">
    <div className="crm-heading"><div><p className="eyebrow">{grant.organization_name}</p><h1>{text.workspace}</h1><p>{text.queueHint}</p></div><Link href={`/${locale}/admin?organization=${grant.organization_id}`}>{text.back}</Link></div>
    <StaffModuleNav locale={locale} organization={grant.organization_id} permissions={grant.permissions} active="crm" />
    {grants.length > 1 ? <nav className="crm-orgs" aria-label={text.organization}>{grants.map((item) => <a key={item.organization_id} href={`?organization=${item.organization_id}`}>{item.organization_name}</a>)}</nav> : null}
    <CrmWorkspace key={grant.organization_id} org={grant.organization_id} permissions={grant.permissions} locale={locale} />
  </main>;
}
