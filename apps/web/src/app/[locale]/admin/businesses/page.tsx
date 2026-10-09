import { notFound, redirect } from "next/navigation";
import { StaffModuleNav } from "../../../../components/staff-module-nav";
import type { components } from "../../../../lib/api-contracts";
import { isLocale } from "../../../../lib/messages";
import { serverApi } from "../../../../lib/server-api";
import BusinessStaff from "./view";

export const metadata = { robots: { index: false, follow: false } };

export default async function BusinessStaffPage({ params, searchParams }: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ organization?: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  let response: Response;
  try { response = await serverApi("/auth/me"); } catch { response = new Response(null, { status: 503 }); }
  if (response.status === 401) redirect(`/${locale}/account`);
  if (!response.ok) return <main><h1>Business tracking</h1><p>Unable to load your account.</p></main>;
  const profile = await response.json() as components["schemas"]["Profile"];
  const requested = (await searchParams).organization;
  const grant = profile.grants.filter((item) => item.permissions.includes("business.track.view"))
    .find((item) => !requested || item.organization_id === requested);
  if (!grant) return <main><h1>Business tracking</h1><p>Access unavailable.</p></main>;
  return <main className="program-main">
    <StaffModuleNav locale={locale} organization={grant.organization_id}
      permissions={grant.permissions} active="businesses" />
    <BusinessStaff org={grant.organization_id} locale={locale}
      canManage={grant.permissions.includes("business.track.manage")} />
  </main>;
}
