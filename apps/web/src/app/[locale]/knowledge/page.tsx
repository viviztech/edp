import { ParticipantModuleNav } from "../../../components/participant-module-nav";
import { notFound, redirect } from "next/navigation";
import type { components } from "../../../lib/api-contracts";
import { isLocale } from "../../../lib/messages";
import { serverApi } from "../../../lib/server-api";
import { words } from "./content";
import KnowledgeWorkspace from "./view";
import "./knowledge.css";

export const metadata = { robots: { index: false, follow: false } };

export default async function KnowledgePage({ params, searchParams }: {
  params: Promise<{ locale: string }>; searchParams: Promise<{ organization?: string }>;
}) {
  const { locale } = await params; if (!isLocale(locale)) notFound(); const t = words[locale];
  let response: Response;
  try { response = await serverApi("/auth/me"); } catch { response = new Response(null, { status: 503 }); }
  if (response.status === 401) redirect(`/${locale}/account`);
  if (!response.ok) return <main id="main" tabIndex={-1}><h1>{t.title}</h1><p>{t.error}</p></main>;
  const profile = await response.json() as components["schemas"]["Profile"];
  const requested = (await searchParams).organization;
  const grant = profile.grants.filter((entry) => entry.permissions.includes("participant.self"))
    .find((entry) => !requested || entry.organization_id === requested);
  if (!grant) return <main id="main" tabIndex={-1}><h1>{t.title}</h1><p>{t.access}</p></main>;
  return <main id="main" tabIndex={-1} className="program-main knowledge-main"><ParticipantModuleNav locale={locale} organization={grant.organization_id} permissions={grant.permissions} active="knowledge" /><KnowledgeWorkspace key={`${grant.organization_id}-${locale}`} org={grant.organization_id} locale={locale} /></main>;
}
