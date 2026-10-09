import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import type { components } from "../../../lib/api-contracts";
import { isLocale } from "../../../lib/messages";
import { serverApi } from "../../../lib/server-api";
import ParticipantTimelineView from "./view";
export const metadata = { robots: { index: false, follow: false } };
export default async function ParticipantPage({ params, searchParams }: { params: Promise<{ locale: string }>; searchParams: Promise<{ organization?: string }> }) {
  const { locale } = await params; if (!isLocale(locale)) notFound();
  let response: Response; try { response = await serverApi("/auth/me"); } catch { response = new Response(null, { status: 503 }); }
  if (response.status === 401) redirect(`/${locale}/account`);
  if (!response.ok) return <main><h1>Participant schedule</h1><p>Unable to load your account.</p></main>;
  const profile = await response.json() as components["schemas"]["Profile"];
  const requested = (await searchParams).organization;
  const grant = profile.grants.filter((item) => item.permissions.includes("participant.self")).find((item) => !requested || item.organization_id === requested);
  if (!grant) return <main><h1>Participant schedule</h1><p>No active participant enrollment.</p><Link href={`/${locale}/account`}>Account</Link></main>;
  return <main className="program-main"><nav><Link href={`/${locale}/attendance?organization=${grant.organization_id}`}>{locale === "ta" ? "\u0b8e\u0ba9\u0ba4\u0bc1 \u0bb5\u0bb0\u0bc1\u0b95\u0bc8" : "My attendance"}</Link> · <Link href={`/${locale}/mentoring?organization=${grant.organization_id}`}>{locale === "ta" ? "\u0b8e\u0ba9\u0ba4\u0bc1 \u0bb5\u0bb4\u0bbf\u0b95\u0bbe\u0b9f\u0bcd\u0b9f\u0bc1\u0ba4\u0bb2\u0bcd" : "My mentoring"}</Link> · <Link href={`/${locale}/business-plan?organization=${grant.organization_id}`}>{locale === "ta" ? "எனது வணிகத் திட்டம்" : "My business plan"}</Link> · <Link href={`/${locale}/businesses?organization=${grant.organization_id}`}>{locale === "ta" ? "எனது தொழில்" : "My business"}</Link></nav><ParticipantTimelineView org={grant.organization_id} locale={locale} /></main>;
}
