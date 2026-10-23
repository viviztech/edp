import Link from "next/link";
import { ArrowLeft, ArrowRight, ArrowUpRight } from "lucide-react";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { publicPage } from "../../../../lib/public-pages";
import { isLocale, messages, type Locale } from "../../../../lib/messages";
import { starterPage, starterPageList } from "../../../../lib/public-site-content";
import { absoluteUrl } from "../../../../lib/site-url";
import { PublicEnquiryForm } from "../../../../components/public-enquiry-form";
import { publicEnquiryPolicy } from "../../../../lib/public-enquiries";

type Props = { params: Promise<{ locale: string; slug: string }> };
export const dynamic = "force-dynamic";

async function published(locale: Locale, slug: string) {
  try { return await publicPage(locale, slug); } catch { return null; }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  if (!isLocale(locale)) return {};
  const page = await published(locale, slug);
  const fallback = starterPage(locale, slug);
  if (!page && !fallback) return { robots: { index: false, follow: false } };
  const other = locale === "en" ? "ta" : "en";
  const counterpart = starterPage(other, slug) || await published(other, slug);
  return {
    title: page?.seo_title || page?.title || fallback?.title,
    description: page?.seo_description || fallback?.intro,
    alternates: {
      canonical: absoluteUrl("/" + locale + "/pages/" + slug),
      languages: {
        [locale]: absoluteUrl("/" + locale + "/pages/" + slug),
        ...(counterpart ? { [other]: absoluteUrl("/" + other + "/pages/" + slug) } : {}),
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
  const group = starterPageList(locale).find((item) => item.slug === slug)?.group;
  const related = starterPageList(locale).filter((item) => item.group === group && item.slug !== slug).slice(0, 4);
  const enquiryPolicy = slug === "contact" ? await publicEnquiryPolicy(locale) : null;
  const labels = locale === "en"
    ? { all: "All pages", related: "In this section", note: "Good to know", next: "Next step" }
    : { all: "அனைத்து பக்கங்களும்", related: "இந்தப் பகுதியில்", note: "அறிந்துகொள்ளுங்கள்", next: "அடுத்த படி" };

  return <main id="main" tabIndex={-1} className="public-detail">
    <div className="public-detail-shell">
      <nav className="public-breadcrumb" aria-label={locale === "en" ? "Breadcrumb" : "பக்க வழி"}>
        <Link href={"/" + locale}>{messages[locale].home}</Link><span aria-hidden="true">/</span>
        <Link href={"/" + locale + "/pages"}>{labels.all}</Link><span aria-hidden="true">/</span>
        <span aria-current="page">{page?.title || fallback?.title}</span>
      </nav>
      <div className="public-detail-grid">
        <article className="public-article">
          <p className="public-eyebrow">{fallback?.eyebrow || messages[locale].title}</p>
          <h1>{page?.title || fallback?.title}</h1>
          {page ? <div className="public-cms-body">{page.body}</div> : <>
            <p className="public-intro">{fallback?.intro}</p>
            <div className="public-topic-list">{fallback?.sections.map((section, index) =>
              <section className="public-topic" key={section.heading}>
                <span className="public-topic-number">{String(index + 1).padStart(2, "0")}</span>
                <div><h2>{section.heading}</h2><p>{section.body}</p></div>
              </section>)}</div>
            {fallback?.note && !(slug === "contact" && enquiryPolicy) && <div className="public-note"><strong>{labels.note}</strong><p>{fallback.note}</p></div>}
            {fallback?.next && <div className="public-next"><span>{labels.next}</span><Link href={"/" + locale + fallback.next.path}>{fallback.next.label}<ArrowRight size={19} aria-hidden="true" /></Link></div>}
          </>}
          {slug === "contact" && <PublicEnquiryForm locale={locale} policy={enquiryPolicy} />}
        </article>
        <aside className="public-side">
          <div className="public-side-card">
            <p>{labels.related}</p>
            {related.map((item) => <Link key={item.slug} href={"/" + locale + "/pages/" + item.slug}>{item.title}<ArrowUpRight size={17} aria-hidden="true" /></Link>)}
            <Link className="public-side-all" href={"/" + locale + "/pages"}>{labels.all}<ArrowLeft size={17} aria-hidden="true" /></Link>
          </div>
        </aside>
      </div>
    </div>
  </main>;
}
