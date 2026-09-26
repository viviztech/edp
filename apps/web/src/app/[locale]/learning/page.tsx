import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import type { components } from "../../../lib/api-contracts";
import { learningMessages } from "../../../lib/learning-messages";
import { isLocale } from "../../../lib/messages";
import { serverApi } from "../../../lib/server-api";
import LearnerWorkspace from "./view";

export const metadata = { robots: { index: false, follow: false } };

export default async function LearningPage({
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
  if (!response.ok) return <main><h1>{text.learnerTitle}</h1><p>{text.error}</p></main>;
  const profile = await response.json() as components["schemas"]["Profile"];
  const requested = (await searchParams).organization;
  const grant = profile.grants
    .filter((item) => item.permissions.includes("lms.learn"))
    .find((item) => !requested || item.organization_id === requested);
  if (!grant) {
    return <main><h1>{text.learnerTitle}</h1><p>{text.empty}</p>
      <Link href={`/${locale}/account`}>Account</Link></main>;
  }
  return <main className="learning-main learner-main">
    <LearnerWorkspace org={grant.organization_id} locale={locale} />
  </main>;
}
