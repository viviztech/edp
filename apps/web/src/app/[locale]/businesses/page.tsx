import { ParticipantModuleNav } from "../../../components/participant-module-nav";
import { notFound, redirect } from "next/navigation";
import type { components } from "../../../lib/api-contracts";
import { isLocale } from "../../../lib/messages";
import { serverApi } from "../../../lib/server-api";
import BusinessTracking from "./view";
import "./businesses.css";

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
  if (!response.ok) return <main id="main" tabIndex={-1}><h1>{locale === "ta" ? "தொழில் முன்னேற்றம்" : "Business tracking"}</h1><p>{locale === "ta" ? "உங்கள் கணக்கை ஏற்ற முடியவில்லை." : "Unable to load your account."}</p></main>;
  const profile = await response.json() as components["schemas"]["Profile"];
  const requested = (await searchParams).organization;
  const grant = profile.grants.filter((item) => item.permissions.includes("participant.self"))
    .find((item) => !requested || item.organization_id === requested);
  if (!grant) return <main id="main" tabIndex={-1}><h1>{locale === "ta" ? "தொழில் முன்னேற்றம்" : "Business tracking"}</h1><p>{locale === "ta" ? "பங்கேற்பாளர் அணுகல் இல்லை." : "No participant access."}</p></main>;
  return <main id="main" tabIndex={-1} className="program-main business-main"><ParticipantModuleNav locale={locale} organization={grant.organization_id} permissions={grant.permissions} active="businesses" /><BusinessTracking org={grant.organization_id} locale={locale} /></main>;
}
