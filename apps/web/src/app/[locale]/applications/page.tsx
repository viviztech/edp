import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { isLocale } from "../../../lib/messages";
import { serverApi } from "../../../lib/server-api";
import { accountHref, intakeId, readIntakeContext } from "../../../lib/intake-context";
import { applicationMessages } from "../../../lib/application-messages";
import ApplicationDraft from "./view";
import "./applications.css";

export const metadata = { robots: { index: false, follow: false } };

export default async function ApplicationsPage({ params, searchParams }: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const query = await searchParams;
  // Reject ambiguous or malformed explicit destinations instead of opening a
  // different intake after sign-in.
  if ((query.organization !== undefined && !intakeId(query.organization))
    || (query.cycle !== undefined && !intakeId(query.cycle))) notFound();
  const intake = readIntakeContext(query, process.env.PUBLIC_ORGANIZATION_ID);
  if (query.cycle !== undefined && !intake.organization) notFound();
  let response: Response;
  try { response = await serverApi("/auth/me"); }
  catch { response = new Response(null, { status: 503 }); }
  if (response.status === 401) redirect(accountHref(locale, intake));
  if (!response.ok) return <main id="main" tabIndex={-1}><h1>{applicationMessages[locale].title}</h1><p role="alert">{applicationMessages[locale].error}</p><Link href={accountHref(locale, intake)}>{locale === "ta" ? "எனது கணக்கு" : "Your account"}</Link></main>;
  return <main id="main" tabIndex={-1} className="application-main"><ApplicationDraft key={`${intake.organization ?? "history"}:${intake.cycle ?? ""}`} locale={locale} org={intake.organization} initialCycle={intake.cycle} /></main>;
}
