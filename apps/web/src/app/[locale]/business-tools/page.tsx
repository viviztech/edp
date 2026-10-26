import { notFound, redirect } from "next/navigation";
import { ParticipantModuleNav } from "../../../components/participant-module-nav";
import type { components } from "../../../lib/api-contracts";
import { toolsCopy } from "../../../lib/business-tools-copy";
import { isLocale } from "../../../lib/messages";
import { serverApi } from "../../../lib/server-api";
import BusinessToolsView from "./view";
import "../businesses/businesses.css";
import "./tools.css";
export const metadata = { robots: { index: false, follow: false } };
export default async function BusinessToolsPage({ params, searchParams }: {
  params: Promise<{ locale: string }>; searchParams: Promise<{ organization?: string }>;
}) {
  const { locale } = await params; if (!isLocale(locale)) notFound();
  let response: Response;
  try { response = await serverApi("/auth/me"); } catch { response = new Response(null, { status: 503 }); }
  if (response.status === 401) redirect(`/${locale}/account`);
  const t = toolsCopy[locale];
  if (!response.ok) return <main id="main" tabIndex={-1}><h1>{t.title}</h1><p>{t.unavailable}</p></main>;
  const profile = await response.json() as components["schemas"]["Profile"];
  const requested = (await searchParams).organization;
  const grant = profile.grants.find(g => g.permissions.includes("participant.self") && (!requested || g.organization_id === requested));
  if (!grant) return <main id="main" tabIndex={-1}><h1>{t.title}</h1><p>{locale === "ta" ? "பங்கேற்பாளர் அணுகல் இல்லை." : "No participant access."}</p></main>;
  return <main id="main" tabIndex={-1} className="program-main business-main tools-main"><ParticipantModuleNav locale={locale} organization={grant.organization_id} permissions={grant.permissions} active="business-tools" />
    <BusinessToolsView key={`${locale}-${grant.organization_id}`} org={grant.organization_id} locale={locale} /></main>;
}
