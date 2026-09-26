import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { StaffModuleNav } from "../../../../components/staff-module-nav";
import type { components } from "../../../../lib/api-contracts";
import { learningMessages } from "../../../../lib/learning-messages";
import { isLocale } from "../../../../lib/messages";
import { serverApi } from "../../../../lib/server-api";
import LearningWorkspace from "./view";

export const metadata = { robots: { index: false, follow: false } };

export default async function LearningAdminPage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ organization?: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const text = learningMessages[locale];
  let response: Response;
  try {
    response = await serverApi("/auth/me");
  } catch {
    response = new Response(null, { status: 503 });
  }
  if (response.status === 401) redirect(`/${locale}/account`);
  if (!response.ok) return <main><h1>{text.workspace}</h1><p>{text.error}</p></main>;
  const profile = await response.json() as components["schemas"]["Profile"];
  const requested = (await searchParams).organization;
  const grants = profile.grants.filter((grant) =>
    grant.permissions.includes("lms.course.view"));
  const grant = grants.find((item) => !requested || item.organization_id === requested);
  if (!grant) {
    return <main><h1>{text.workspace}</h1><p>{text.error}</p>
      <Link href={`/${locale}/admin`}>Admin</Link></main>;
  }
  return <main className="learning-main">
    <StaffModuleNav
      locale={locale}
      organization={grant.organization_id}
      permissions={grant.permissions}
      active="learning"
    />
    <header className="learning-heading">
      <div><p className="eyebrow">{text.eyebrow}</p><h1>{text.title}</h1>
        <p>{text.intro}</p></div>
      <Link href={`/${locale}/admin?organization=${grant.organization_id}`}>Admin</Link>
    </header>
    <LearningWorkspace
      org={grant.organization_id}
      locale={locale}
      permissions={grant.permissions}
    />
  </main>;
}
