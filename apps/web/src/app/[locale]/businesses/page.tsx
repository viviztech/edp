import { notFound, redirect } from "next/navigation";
import Link from "next/link";
import type { components } from "../../../lib/api-contracts";
import { isLocale } from "../../../lib/messages";
import { serverApi } from "../../../lib/server-api";
import BusinessTracking from "./view";
import { ParticipantNavigation } from "../../../components/participant-navigation";

export const metadata = { robots: { index: false, follow: false } };

export default async function BusinessPage({ params, searchParams }: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ organization?: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  let response: Response;
  try { response = await serverApi("/auth/me"); } catch { response = new Response(null, { status: 503 }); }
  if (response.status === 401) redirect(`/${locale}/account`);
  if (!response.ok) return <main id="main"><h1>{locale === "ta" ? "எனது தொழில்" : "My business"}</h1><p role="alert">{locale === "ta" ? "உங்கள் கணக்கை ஏற்ற முடியவில்லை." : "Unable to load your account."}</p></main>;
  const profile = await response.json() as components["schemas"]["Profile"];
  const requested = (await searchParams).organization;
  const grant = profile.grants.filter((item) => item.permissions.includes("participant.self"))
    .find((item) => !requested || item.organization_id === requested);
  if (!grant) return <main id="main"><h1>{locale === "ta" ? "எனது தொழில்" : "My business"}</h1><p>{locale === "ta" ? "பங்கேற்பாளர் அணுகல் இல்லை." : "You do not have participant access."}</p><Link href={`/${locale}/account`}>{locale === "ta" ? "எனது கணக்கு" : "My account"}</Link></main>;
  return <main id="main" className="program-main participant-workspace"><ParticipantNavigation locale={locale} organization={grant.organization_id} permissions={grant.permissions} active="businesses" /><BusinessTracking org={grant.organization_id} locale={locale} /></main>;
}
