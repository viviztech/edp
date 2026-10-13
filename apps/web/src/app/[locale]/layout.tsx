import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import localFont from "next/font/local";
import { notFound } from "next/navigation";
import { authMessages } from "../../lib/auth-messages";
import { PublicNavigation } from "../../components/public-navigation";
import { PublicFooter } from "../../components/public-footer";
import { isLocale, messages } from "../../lib/messages";
import {
  publicNavLabels,
  starterPageList,
} from "../../lib/public-site-content";
import { siteUrl } from "../../lib/site-url";
import "../styles.css";
import "../public.css";

const displayFont = localFont({
  src: "../../assets/fonts/sora.woff2",
  variable: "--font-public-display",
  weight: "100 800",
  display: "swap",
});
const bodyFont = localFont({
  src: "../../assets/fonts/hanken-grotesk.woff2",
  variable: "--font-public-body",
  weight: "100 900",
  display: "swap",
});
const tamilFont = localFont({
  src: "../../assets/fonts/noto-sans-tamil.woff2",
  variable: "--font-public-tamil",
  weight: "100 900",
  display: "swap",
  preload: false,
  adjustFontFallback: false,
});

export const metadata: Metadata = {
  metadataBase: siteUrl(),
  icons: { icon: "/cse-logo.png", apple: "/cse-logo.png" },
};

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const text = messages[locale];
  const labels = publicNavLabels[locale];
  const pages = starterPageList(locale);
  return (
    <html
      lang={locale}
      className={`${displayFont.variable} ${bodyFont.variable} ${tamilFont.variable}`}
    >
      <body className="public-site-body">
        <a className="skip" href="#main">
          {text.skip}
        </a>
        <header className="site-header">
          <div className="site-header-inner">
            <Link
              className="identity"
              href={`/${locale}`}
              aria-label={text.organization}
            >
              <Image
                className="identity-logo"
                src="/cse-logo.png"
                width={52}
                height={52}
                alt=""
                preload
              />
              <span className="identity-wordmark">
                <strong>CSJE</strong>
                <small>
                  {locale === "en"
                    ? "Entrepreneurs Hub"
                    : "தொழில்முனைவோர் மையம்"}
                </small>
              </span>
            </Link>
            <PublicNavigation
              locale={locale}
              navigationLabel={text.navigation}
              labels={{
                ...labels,
                account: authMessages[locale].title,
                language: text.language,
              }}
              program={pages
                .filter((page) => page.group === "program")
                .map((page) => ({
                  title: page.title,
                  href: `/${locale}/pages/${page.slug}`,
                }))}
              support={pages
                .filter((page) => page.group === "support")
                .map((page) => ({
                  title: page.title,
                  href: `/${locale}/pages/${page.slug}`,
                }))}
            />
          </div>
        </header>
        {children}
        <PublicFooter locale={locale} />
      </body>
    </html>
  );
}
