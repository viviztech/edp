import { notFound, redirect } from "next/navigation";
import { StaffModuleNav } from "../../../../components/staff-module-nav";
import type { components } from "../../../../lib/api-contracts";
import { enquiryWords } from "../../../../lib/enquiry-content";
import { isLocale } from "../../../../lib/messages";
import { serverApi } from "../../../../lib/server-api";
import EnquiryInbox from "./view";
export const metadata = { robots: { index: false, follow: false } };
export default async function Enquiries({ params, searchParams }: {
  params: Promise<{ locale: string }>; searchParams: Promise<{ organization?: string }>;
}) {
  const { locale } = await params; if (!isLocale(locale)) notFound(); const t = enquiryWords[locale];
  let response: Response;
  try { response = await serverApi("/auth/me"); } catch { return <main id="main" tabIndex={-1}><p role="alert">{t.staffError}</p></main>; }
  if (response.status === 401) redirect(`/${locale}/account`);
  if (!response.ok) return <main id="main" tabIndex={-1}><p role="alert">{t.staffError}</p></main>;
  const profile: components["schemas"]["Profile"] = await response.json(); const org = (await searchParams).organization;
  const grants = profile.grants.filter(grant => grant.permissions.includes("enquiry.view"));
  const grant = grants.find(value => !org || value.organization_id === org);
  if (!grant) return <main id="main" tabIndex={-1}><p>{t.denied}</p></main>;
  return <main id="main" tabIndex={-1} className="cms-main"><p className="eyebrow">{grant.organization_name}</p><h1>{t.workspace}</h1>
    <nav className="actions" aria-label={locale === "en" ? "Organizations" : "நிறுவனங்கள்"}>{grants.map(value => <a key={value.organization_id} href={`?organization=${value.organization_id}`}>{value.organization_name}</a>)}</nav>
    <StaffModuleNav locale={locale} organization={grant.organization_id} permissions={grant.permissions} active="enquiries" />
    <EnquiryInbox key={grant.organization_id} org={grant.organization_id} locale={locale} permissions={grant.permissions} />
  </main>;
}
