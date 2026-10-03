import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import type { components } from "../../../lib/api-contracts";
import { attendanceMessages } from "../../../lib/attendance-messages";
import { isLocale } from "../../../lib/messages";
import { serverApi } from "../../../lib/server-api";
import LearnerAttendance from "./view";

export const metadata = { robots: { index: false, follow: false } };

export default async function AttendancePage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ organization?: string; token?: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const query = await searchParams;
  const text = attendanceMessages[locale];
  let response: Response;
  try { response = await serverApi("/auth/me"); } catch { response = new Response(null, { status: 503 }); }
  if (response.status === 401) redirect(`/${locale}/account`);
  if (!response.ok) return <main><h1>{text.learnerTitle}</h1><p>{text.error}</p></main>;
  const profile = await response.json() as components["schemas"]["Profile"];
  const grant = profile.grants
    .filter((item) => item.permissions.includes("participant.self"))
    .find((item) => !query.organization || item.organization_id === query.organization);
  if (!grant) return <main><h1>{text.learnerTitle}</h1><p>{text.error}</p><Link href={`/${locale}/account`}>Account</Link></main>;
  return <main className="program-main">
    <LearnerAttendance org={grant.organization_id} locale={locale} initialToken={query.token ?? ""} />
  </main>;
}
