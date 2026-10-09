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
    <header className="site-header"><div className="site-header-inner"><Link className="identity" href={`/${locale}`}><span className="identity-mark" aria-hidden="true" /><span>{text.organization}</span></Link>
      <nav className="site-nav" aria-label={text.navigation}>
        <Link href={`/${locale}`}>{text.home}</Link>
        {navigation.map((page) => <Link key={page.id} href={`/${locale}/pages/${page.slug}`}>{page.title}</Link>)}
        <Link href={`/${locale}/pages`}>{cmsMessages[locale].pages}</Link>
        <Link className="site-account" href={`/${locale}/account`}>{authMessages[locale].title}</Link>
        <Link className="site-language" href={`/${locale === "en" ? "ta" : "en"}`} lang={locale === "en" ? "ta" : "en"}>{text.language}</Link>
      </nav>
    </div></header>
    {children}
    <footer className="site-footer"><div><strong>{text.organization}</strong><span>{text.title}</span></div></footer>
  </body></html>;
}
