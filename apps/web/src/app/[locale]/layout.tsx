import Link from "next/link";
import { notFound } from "next/navigation";
import { authMessages } from "../../lib/auth-messages";
import { isLocale, messages } from "../../lib/messages";
import "../styles.css";
import { cmsMessages } from "../../lib/cms-messages";

export default async function LocaleLayout({ children, params }: {
  children: React.ReactNode; params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const text = messages[locale];
  return <html lang={locale}><body>
    <a className="skip" href="#main">{text.skip}</a>
    <header><Link className="identity" href={`/${locale}`}>{text.organization}</Link>
      <nav aria-label={text.language}><Link href={`/${locale}/pages`}>{cmsMessages[locale].pages}</Link>{" | "}<Link href={"/" + locale + "/account"}>{authMessages[locale].title}</Link>{" · "}<Link href={`/${locale === "en" ? "ta" : "en"}`}>{text.language}</Link></nav>
    </header>
    {children}
    <footer>{text.title}</footer>
  </body></html>;
}
