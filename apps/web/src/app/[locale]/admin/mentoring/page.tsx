import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { StaffModuleNav } from "../../../../components/staff-module-nav";
import type { components } from "../../../../lib/api-contracts";
import { mentoringMessages } from "../../../../lib/mentoring-messages";
import { isLocale } from "../../../../lib/messages";
import { serverApi } from "../../../../lib/server-api";
import MentoringWorkspace from "./view";

export const metadata = { robots: { index: false, follow: false } };

export default async function MentoringAdminPage({ params, searchParams }: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ organization?: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const text = mentoringMessages[locale];
  let response: Response;
  try { response = await serverApi("/auth/me"); } catch { response = new Response(null, { status: 503 }); }
  if (response.status === 401) redirect(`/${locale}/account`);
  if (!response.ok) return <main><h1>{text.workspace}</h1><p>{text.error}</p></main>;
  const profile = await response.json() as components["schemas"]["Profile"];
  const requested = (await searchParams).organization;
  const grant = profile.grants.filter((item) => item.permissions.includes("mentoring.view"))
    .find((item) => !requested || item.organization_id === requested);
  if (!grant) return <main><h1>{text.workspace}</h1><p>{text.error}</p></main>;
  return <main className="program-main">
    <StaffModuleNav locale={locale} organization={grant.organization_id}
      permissions={grant.permissions} active="mentoring" />
    <header className="program-heading"><div><p className="eyebrow">{text.eyebrow}</p>
      <h1>{text.title}</h1><p>{text.intro}</p></div>
      <div><Link href={`/${locale}/admin/business-plans?organization=${grant.organization_id}`}>
        {locale === "ta" ? "வணிகத் திட்ட மதிப்பாய்வுகள்" : "Business plan reviews"}</Link> · <Link href={`/${locale}/admin?organization=${grant.organization_id}`}>Admin</Link></div>
    </header>
    <MentoringWorkspace org={grant.organization_id} locale={locale}
      canAdmin={grant.permissions.includes("mentoring.admin")} />
  </main>;
}
