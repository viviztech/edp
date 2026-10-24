import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { ParticipantModuleNav } from "../../../components/participant-module-nav";
import type { components } from "../../../lib/api-contracts";
import { intakeId } from "../../../lib/intake-context";
import { isLocale } from "../../../lib/messages";
import { serverApi } from "../../../lib/server-api";
import { updateMessages } from "./content";
import Updates from "./view";
import "./updates.css";

export const metadata = { robots: { index: false, follow: false } };
export default async function UpdatesPage({ params, searchParams }: {
  params: Promise<{ locale: string }>; searchParams: Promise<{ organization?: string | string[] }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const t = updateMessages[locale], query = await searchParams;
  if (query.organization !== undefined && !intakeId(query.organization)) notFound();
  const requested = intakeId(query.organization);
  let response: Response;
  try { response = await serverApi("/auth/me"); } catch { response = new Response(null, { status: 503 }); }
  if (response.status === 401) redirect(`/${locale}/account`);
  if (!response.ok) return <main id="main" tabIndex={-1}><h1>{t.title}</h1><p role="alert">{t.error}</p><Link href={`/${locale}/account`}>{t.back}</Link></main>;
  const profile = await response.json() as components["schemas"]["Profile"];
  const grant = profile.grants.filter(value => value.permissions.includes("participant.self")).find(value => !requested || value.organization_id === requested);
  if (!grant) return <main id="main" tabIndex={-1}><h1>{t.title}</h1><p>{t.access}</p><Link href={`/${locale}/account`}>{t.back}</Link></main>;
  return <main id="main" tabIndex={-1} className="program-main updates-main">
    <ParticipantModuleNav locale={locale} organization={grant.organization_id} permissions={grant.permissions} active="updates" />
    <Updates key={`${grant.organization_id}-${locale}`} org={grant.organization_id} locale={locale} />
  </main>;
}
