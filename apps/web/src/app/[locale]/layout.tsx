import Link from "next/link";
import { notFound } from "next/navigation";
import { authMessages } from "../../lib/auth-messages";
import { isLocale, messages } from "../../lib/messages";
import "../styles.css";
import { cmsMessages } from "../../lib/cms-messages";
import { publicNavigation } from "../../lib/public-navigation";

export default async function LocaleLayout({ children, params }: {
  children: React.ReactNode; params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const text = messages[locale];
  const navigation = await publicNavigation(locale);
  return <html lang={locale}><body>
    <a className="skip" href="#main">{text.skip}</a>
    <header><Link className="identity" href={`/${locale}`}>{text.organization}</Link>
      <nav className="site-nav" aria-label={text.navigation}>
        <Link href={`/${locale}`}>{text.home}</Link>
        {navigation.map((page) => <Link key={page.id} href={`/${locale}/pages/${page.slug}`}>{page.title}</Link>)}
        <Link href={`/${locale}/pages`}>{cmsMessages[locale].pages}</Link>
        <Link href={`/${locale}/account`}>{authMessages[locale].title}</Link>
        <Link href={`/${locale === "en" ? "ta" : "en"}`} lang={locale === "en" ? "ta" : "en"}>{text.language}</Link>
      </nav>
    </header>
    {children}
    <footer>{text.title}</footer>
  </body></html>;
}
