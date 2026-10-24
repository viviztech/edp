import { notFound, redirect } from "next/navigation";
import { StaffModuleNav } from "../../../../components/staff-module-nav";
import type { components } from "../../../../lib/api-contracts";
import { mediaAdminMessages } from "../../../../lib/media-admin-messages";
import { isLocale } from "../../../../lib/messages";
import { serverApi } from "../../../../lib/server-api";
import MediaMetadata from "./view";
import "../content/workspace.css";

export const metadata = { robots: { index: false, follow: false } };
export default async function MediaAdminPage({ params, searchParams }: {
  params: Promise<{ locale: string }>; searchParams: Promise<{ organization?: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const text = mediaAdminMessages[locale];
  let response: Response;
  try { response = await serverApi("/auth/me"); } catch { response = new Response(null, { status: 503 }); }
  if (response.status === 401) redirect(`/${locale}/account`);
  if (!response.ok) return <main id="main" tabIndex={-1}><h1>{text.title}</h1><p role="alert">{text.error}</p></main>;
  const profile = await response.json() as components["schemas"]["Profile"];
  const organization = (await searchParams).organization;
  const grant = profile.grants.find(entry => (!organization || entry.organization_id === organization) && entry.permissions.includes("cms.asset.view"));
  if (!grant) return <main id="main" tabIndex={-1}><h1>{text.title}</h1><p>{text.denied}</p></main>;
  return <main id="main" tabIndex={-1} className="content-admin-main">
    <StaffModuleNav locale={locale} organization={grant.organization_id} permissions={grant.permissions} active="media" />
    <h1>{text.title}</h1><p>{text.intro}</p>
    <MediaMetadata key={`${locale}-${grant.organization_id}`} org={grant.organization_id} locale={locale} permissions={grant.permissions} />
  </main>;
}
