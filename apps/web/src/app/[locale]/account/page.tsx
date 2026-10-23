import { notFound } from "next/navigation";
import { authMessages } from "../../../lib/auth-messages";
import { isLocale } from "../../../lib/messages";
import { intakeId, readIntakeContext, type IntakeSearch } from "../../../lib/intake-context";
import Account from "./view";

export default async function AccountPage({ params, searchParams }: { params: Promise<{ locale: string }>; searchParams: Promise<IntakeSearch> }) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const query = await searchParams;
  if (query.organization !== undefined && !intakeId(query.organization)) notFound();
  const intake = readIntakeContext(query, process.env.PUBLIC_ORGANIZATION_ID);
  if (query.cycle !== undefined && (!intakeId(query.cycle) || !intake.organization)) notFound();
  return <main id="main" tabIndex={-1} className="account-shell"><Account text={authMessages[locale]} locale={locale} intake={intake} /></main>;
}
