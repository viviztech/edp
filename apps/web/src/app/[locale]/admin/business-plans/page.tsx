import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { StaffModuleNav } from "../../../../components/staff-module-nav";
import type { components } from "../../../../lib/api-contracts";
import { isLocale } from "../../../../lib/messages";
import { serverApi } from "../../../../lib/server-api";
import MentorPlanReviews from "./view";

export const metadata = { robots: { index: false, follow: false } };

export default async function BusinessPlansAdminPage({ params, searchParams }: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ organization?: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  let response: Response;
  try { response = await serverApi("/auth/me"); } catch { response = new Response(null, { status: 503 }); }
  if (response.status === 401) redirect(`/${locale}/account`);
  if (!response.ok) return <main><h1>Business plan reviews</h1><p>Unable to load your account.</p></main>;
  const profile = await response.json() as components["schemas"]["Profile"];
  const requested = (await searchParams).organization;
  const grant = profile.grants.filter((item) => item.permissions.includes("mentoring.manage"))
    .find((item) => !requested || item.organization_id === requested);
  if (!grant) return <main><h1>Business plan reviews</h1><p>Access unavailable.</p></main>;
  return <main className="program-main">
    <StaffModuleNav locale={locale} organization={grant.organization_id}
      permissions={grant.permissions} active="mentoring" />
    <header className="program-heading"><div><p className="eyebrow">B01</p>
      <h1>{locale === "ta" ? "வணிகத் திட்ட மதிப்பாய்வுகள்" : "Business plan reviews"}</h1></div>
      <Link href={`/${locale}/admin/mentoring?organization=${grant.organization_id}`}>
        {locale === "ta" ? "வழிகாட்டுதல்" : "Mentoring"}</Link>
    </header>
    <MentorPlanReviews org={grant.organization_id} locale={locale} />
  </main>;
}
