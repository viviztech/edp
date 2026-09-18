import { notFound } from "next/navigation";
import { authMessages } from "../../../lib/auth-messages";
import { isLocale } from "../../../lib/messages";
import Account from "./view";

export default async function AccountPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  return <main id="main"><Account text={authMessages[locale]} locale={locale} /></main>;
}
