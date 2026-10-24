import { notFound } from "next/navigation";
import AccountChallenge from "../../../../components/account-challenge";
import { isLocale } from "../../../../lib/messages";

export const metadata = { robots: { index: false, follow: false }, referrer: "no-referrer" as const };
export default async function ResetPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  return <main id="main" tabIndex={-1} className="account-shell"><AccountChallenge locale={locale} purpose="reset" /></main>;
}
