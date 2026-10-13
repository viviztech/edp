import Link from "next/link";
import { ArrowLeft, ArrowRight, ArrowUpRight } from "lucide-react";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { publicPage } from "../../../../lib/public-pages";
import { isLocale, messages, type Locale } from "../../../../lib/messages";
import {
  starterPage,
  starterPageList,
} from "../../../../lib/public-site-content";
import { absoluteUrl } from "../../../../lib/site-url";
import { publicLaunch, launchCopy } from "../../../../lib/public-launch";

type Props = { params: Promise<{ locale: string; slug: string }> };
export const dynamic = "force-dynamic";

async function published(locale: Locale, slug: string) {
  try {
    return await publicPage(locale, slug);
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  if (!isLocale(locale)) return {};
  const page = await published(locale, slug);
  const fallback = starterPage(locale, slug);
  if (!page && !fallback) return { robots: { index: false, follow: false } };
  const other = locale === "en" ? "ta" : "en";
  const counterpart =
    starterPage(other, slug) || (await published(other, slug));
  return {
    title: page?.seo_title || page?.title || fallback?.title,
    description: page?.seo_description || fallback?.intro,
    alternates: {
      canonical: absoluteUrl("/" + locale + "/pages/" + slug),
      languages: {
        [locale]: absoluteUrl("/" + locale + "/pages/" + slug),
        ...(counterpart
          ? { [other]: absoluteUrl("/" + other + "/pages/" + slug) }
          : {}),
      },
    },
  };
}

export default async function Page({ params }: Props) {
  const { locale, slug } = await params;
  if (!isLocale(locale)) notFound();
  const page = await published(locale, slug);
  const fallback = starterPage(locale, slug);
  if (!page && !fallback) notFound();
  const group = starterPageList(locale).find(
    (item) => item.slug === slug,
  )?.group;
  const related = starterPageList(locale)
    .filter((item) => item.group === group && item.slug !== slug)
    .slice(0, 4);
  const labels =
    locale === "en"
      ? {
          all: "All pages",
          related: "In this section",
          note: "Good to know",
          next: "Next step",
        }
      : {
          all: "அனைத்து பக்கங்களும்",
          related: "இந்தப் பகுதியில்",
          note: "அறிந்துகொள்ளுங்கள்",
          next: "அடுத்த படி",
        };

  const launch = publicLaunch();
  return (
    <main id="main" className="public-detail">
      <div className="public-detail-shell">
        <nav
          className="public-breadcrumb"
          aria-label={locale === "en" ? "Breadcrumb" : "பக்க வழி"}
        >
          <Link href={"/" + locale}>{messages[locale].home}</Link>
          <span aria-hidden="true">/</span>
          <Link href={"/" + locale + "/pages"}>{labels.all}</Link>
          <span aria-hidden="true">/</span>
          <span aria-current="page">{page?.title || fallback?.title}</span>
        </nav>
        <div className="public-detail-grid">
          <article className="public-article">
            <p className="public-eyebrow">
              {fallback?.eyebrow || messages[locale].title}
            </p>
            <h1>{page?.title || fallback?.title}</h1>
            {slug === "contact" &&
              (launch.email || launch.phone || launch.whatsapp) && (
                <div className="public-actions contact-channels">
                  {launch.email && (
                    <a
                      className="public-button public-button-primary"
                      href={`mailto:${launch.email}`}
                    >
                      {launchCopy[locale].email}
                    </a>
                  )}
                  {launch.phone && (
                    <a
                      className="public-button public-button-outline"
                      href={`tel:${launch.phone.replace(/[ ()-]/g, "")}`}
                    >
                      {launchCopy[locale].phone}
                    </a>
                  )}
                  {launch.whatsapp && (
                    <a
                      className="public-button public-button-outline"
                      href={`https://wa.me/${launch.whatsapp}`}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {launchCopy[locale].whatsapp}
                    </a>
                  )}
                </div>
              )}
            {launch.demo && (slug === "apply" || slug === "contact") && (
              <div className="public-note launch-demo-note">
                <strong>
                  {locale === "en"
                    ? "Explore the platform in action"
                    : "தளத்தைச் செயலில் அறியுங்கள்"}
                </strong>
                <p>
                  {locale === "en"
                    ? "Try profile creation, a sample application, learning and mentoring in the interactive demo. Sample data does not create a real account or application."
                    : "செயல்விளக்கத்தில் மாதிரிக் கணக்கு, விண்ணப்பம், கற்றல், வழிகாட்டுதல் ஆகியவற்றை முயலுங்கள். உண்மையான கணக்கோ விண்ணப்பமோ உருவாகாது."}
                </p>
                <Link className="public-text-link" href={`/${locale}/demo`}>
                  {launchCopy[locale].demo}
                  <ArrowUpRight size={18} aria-hidden="true" />
                </Link>
              </div>
            )}
            {page ? (
              <div className="public-cms-body">{page.body}</div>
            ) : (
              <>
                <p className="public-intro">{fallback?.intro}</p>
                <div className="public-topic-list">
                  {fallback?.sections.map((section, index) => (
                    <section className="public-topic" key={section.heading}>
                      <span className="public-topic-number">
                        {String(index + 1).padStart(2, "0")}
                      </span>
                      <div>
                        <h2>{section.heading}</h2>
                        <p>{section.body}</p>
                      </div>
                    </section>
                  ))}
                </div>
                {fallback?.note && (
                  <div className="public-note">
                    <strong>{labels.note}</strong>
                    <p>{fallback.note}</p>
                  </div>
                )}
                {fallback?.next && (
                  <div className="public-next">
                    <span>{labels.next}</span>
                    <Link href={"/" + locale + fallback.next.path}>
                      {fallback.next.label}
                      <ArrowRight size={19} aria-hidden="true" />
                    </Link>
                  </div>
                )}
              </>
            )}
          </article>
          <aside className="public-side">
            <div className="public-side-card">
              <p>{labels.related}</p>
              {related.map((item) => (
                <Link
                  key={item.slug}
                  href={"/" + locale + "/pages/" + item.slug}
                >
                  {item.title}
                  <ArrowUpRight size={17} aria-hidden="true" />
                </Link>
              ))}
              <Link className="public-side-all" href={"/" + locale + "/pages"}>
                {labels.all}
                <ArrowLeft size={17} aria-hidden="true" />
              </Link>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}
