import { ParticipantModuleNav } from "../../../components/participant-module-nav";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import type { components } from "../../../lib/api-contracts";
import { isLocale } from "../../../lib/messages";
import { serverApi } from "../../../lib/server-api";
import BusinessPlanView from "./view";

export const metadata = { robots: { index: false, follow: false } };

export default async function BusinessPlanPage({ params, searchParams }: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ organization?: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  let response: Response;
  try { response = await serverApi("/auth/me"); } catch { response = new Response(null, { status: 503 }); }
  if (response.status === 401) redirect(`/${locale}/account`);
  if (!response.ok) return <main id="main" tabIndex={-1}><h1>{locale === "ta" ? "வணிகத் திட்டம்" : "Business plan"}</h1><p>{locale === "ta" ? "உங்கள் கணக்கை ஏற்ற முடியவில்லை." : "Unable to load your account."}</p></main>;
  const profile = await response.json() as components["schemas"]["Profile"];
  const requested = (await searchParams).organization;
  const grant = profile.grants.filter((item) => item.permissions.includes("participant.self"))
    .find((item) => !requested || item.organization_id === requested);
  if (!grant) return <main id="main" tabIndex={-1}><h1>{locale === "ta" ? "வணிகத் திட்டம்" : "Business plan"}</h1><p>{locale === "ta" ? "செயலில் உள்ள பங்கேற்பாளர் சேர்க்கை இல்லை." : "No active participant enrollment."}</p>
    <Link href={`/${locale}/account`}>{locale === "ta" ? "எனது கணக்கு" : "My account"}</Link></main>;
  return <main id="main" tabIndex={-1} className="program-main"><ParticipantModuleNav locale={locale} organization={grant.organization_id} permissions={grant.permissions} active="business-plan" /><BusinessPlanView org={grant.organization_id} locale={locale} /></main>;
}
