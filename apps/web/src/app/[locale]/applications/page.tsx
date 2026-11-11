import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { isLocale } from "../../../lib/messages";
import { serverApi } from "../../../lib/server-api";
import type { components } from "../../../lib/api-contracts";
import { ParticipantNavigation } from "../../../components/participant-navigation";
import ApplicationDraft from "./view";

export const metadata = { robots: { index: false, follow: false } };

export default async function ApplicationsPage({ params, searchParams }: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ organization?: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const organization = (await searchParams).organization;
  if (!organization || !/^[0-9a-f-]{36}$/i.test(organization)) {
    return <main id="main" className="application-main"><h1>Applications</h1><p>Select a program organization from your account.</p><Link href={`/${locale}/account`}>Your account</Link></main>;
  }
  const response = await serverApi("/auth/me");
  if (response.status === 401) redirect(`/${locale}/account`);
  if (!response.ok) return <main id="main"><p role="alert">The application could not load.</p></main>;
  const profile = await response.json() as components["schemas"]["Profile"];
  const grant = profile.grants.find((item) => item.organization_id === organization);
  return <main id="main" className="application-main participant-workspace">
    <ParticipantNavigation locale={locale} organization={organization} permissions={grant?.permissions ?? []} active="applications" />
    <ApplicationDraft locale={locale} org={organization} />
  </main>;
}
