import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { authMessages } from "../../lib/auth-messages";
import { PublicNavigation } from "../../components/public-navigation";
import { isLocale, messages } from "../../lib/messages";
import "../styles.css";
import { publicNavLabels, starterPageList } from "../../lib/public-site-content";
import { siteUrl } from "../../lib/site-url";

export const metadata: Metadata = {
  metadataBase: siteUrl(),
  icons: {
    icon: "/cse-logo.png",
    apple: "/cse-logo.png",
  },
};

export default async function LocaleLayout({ children, params }: {
  children: React.ReactNode; params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const text = messages[locale];
  const labels = publicNavLabels[locale];
  const pages = starterPageList(locale);
  const program = pages.filter((page) => page.group === "program");
  const support = pages.filter((page) => page.group === "support");
  return <html lang={locale}><body>
    <a className="skip" href="#main">{text.skip}</a>
    <header className="site-header"><div className="site-header-inner"><Link className="identity" href={`/${locale}`} aria-label={text.organization}><Image className="identity-logo" src="/cse-logo.png" width={88} height={88} alt="" priority /></Link>
      <PublicNavigation
        locale={locale}
        navigationLabel={text.navigation}
        labels={{ ...labels, account: authMessages[locale].title, language: text.language }}
        program={program.map((page) => ({ title: page.title, href: `/${locale}/pages/${page.slug}` }))}
        support={support.map((page) => ({ title: page.title, href: page.slug === "resources" ? `/${locale}/resources` : `/${locale}/pages/${page.slug}` }))}
      />
    </div></header>
    {children}
    <footer className="site-footer"><div><div className="site-footer-brand"><Image src="/cse-logo.png" width={68} height={68} alt="" /><strong>{text.organization}</strong></div><span>{text.title}</span></div></footer>
  </body></html>;
}
