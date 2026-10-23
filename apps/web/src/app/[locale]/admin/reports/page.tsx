import { notFound, redirect } from "next/navigation";
import { StaffModuleNav } from "../../../../components/staff-module-nav";
import type { components } from "../../../../lib/api-contracts";
import { isLocale } from "../../../../lib/messages";
import { serverApi } from "../../../../lib/server-api";
import { words } from "../../impact/content";
import ReportsWorkspace from "./view";
import "../../impact/impact.css";

export const metadata = { robots: { index: false, follow: false } };
export default async function ReportsPage({ params, searchParams }: {
  params: Promise<{ locale: string }>; searchParams: Promise<{ organization?: string }>;
}) {
  const { locale } = await params; if (!isLocale(locale)) notFound(); const t = words[locale];
  let response: Response;
  try { response = await serverApi("/auth/me"); } catch { response = new Response(null, { status: 503 }); }
  if (response.status === 401) redirect(`/${locale}/account`);
  if (!response.ok) return <main id="main"><h1>{t.reports}</h1><p>{t.error}</p></main>;
  const profile = await response.json() as components["schemas"]["Profile"];
  const requested = (await searchParams).organization;
  const grant = profile.grants.filter((entry) => entry.permissions.some((permission) => ["report.view", "impact.manage"].includes(permission)))
    .find((entry) => !requested || entry.organization_id === requested);
  if (!grant) return <main id="main"><h1>{t.reports}</h1><p>{t.access}</p></main>;
  return <main id="main" className="program-main impact-main"><StaffModuleNav locale={locale} organization={grant.organization_id} permissions={grant.permissions} active="reports" />
    <ReportsWorkspace key={`${grant.organization_id}-${locale}`} org={grant.organization_id} locale={locale}
      canView={grant.permissions.includes("report.view")} canExport={grant.permissions.includes("report.export")} canManage={grant.permissions.includes("impact.manage")} /></main>;
}
