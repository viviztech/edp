import Link from "next/link";
import { ArrowRight, ArrowUpRight } from "lucide-react";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import type { components } from "../../../lib/api-contracts";
import { publicPages } from "../../../lib/public-pages";
import { isLocale } from "../../../lib/messages";
import { publicNavLabels, starterPageList } from "../../../lib/public-site-content";
import { absoluteUrl } from "../../../lib/site-url";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await params;
  if (!isLocale(locale)) return {};
  const title = publicNavLabels[locale].all;
  return {
    title,
    description: locale === "en" ? "Explore the Entrepreneurship Development Program and its public information pages." : "தொழில்முனைவோர் மேம்பாட்டுத் திட்டத்தின் பொதுத் தகவல் பக்கங்களை ஆராயுங்கள்.",
    alternates: { canonical: absoluteUrl("/" + locale + "/pages"), languages: { en: absoluteUrl("/en/pages"), ta: absoluteUrl("/ta/pages") } },
  };
}

export default async function Pages({ params, searchParams }: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ cursor?: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const labels = publicNavLabels[locale];
  const pages = starterPageList(locale);
  let data: components["schemas"]["PublicList"] | null = null;
  try {
    const response = await publicPages(locale, undefined, (await searchParams).cursor);
    if (response?.ok) data = await response.json();
  } catch {}
  const additional = data?.items.filter((item) => !pages.some((page) => page.slug === item.slug)) ?? [];
  const groups = [
    { key: "program", title: labels.program },
    { key: "support", title: labels.support },
    { key: "connect", title: locale === "en" ? "Get started" : "தொடங்குங்கள்" },
  ] as const;
  const editorial = [
    { title: labels.news, path: "/content/news" },
    { title: labels.events, path: "/content/event" },
    { title: labels.faq, path: "/content/faq" },
    { title: labels.stories, path: "/content/testimonial" },
  ];
  return <main id="main" className="public-index">
    <div className="public-index-shell">
      <p className="public-eyebrow">{locale === "en" ? "Explore the program" : "திட்டத்தை ஆராயுங்கள்"}</p>
      <h1>{labels.all}</h1>
      <p className="public-index-lead">{locale === "en" ? "Find the program information, practical support, and updates you need for your next step." : "உங்கள் அடுத்த படிக்குத் தேவையான திட்டத் தகவல்கள், நடைமுறை ஆதரவு, புதிய செய்திகளை இங்கே கண்டறியுங்கள்."}</p>
      {groups.map((group) => <section className="public-index-group" key={group.key} aria-labelledby={"group-" + group.key}>
        <div><span className="public-index-line" /><h2 id={"group-" + group.key}>{group.title}</h2></div>
        <div className="public-index-grid">{pages.filter((page) => page.group === group.key).map((page) =>
          <Link key={page.slug} href={"/" + locale + "/pages/" + page.slug}><strong>{page.title}</strong><ArrowUpRight size={20} aria-hidden="true" /></Link>)}</div>
      </section>)}
      <section className="public-index-group" aria-labelledby="group-updates">
        <div><span className="public-index-line" /><h2 id="group-updates">{labels.updates}</h2></div>
        <div className="public-index-grid">{editorial.map((item) =>
          <Link key={item.path} href={"/" + locale + item.path}><strong>{item.title}</strong><ArrowUpRight size={20} aria-hidden="true" /></Link>)}</div>
      </section>
      {additional.length > 0 && <section className="public-index-group" aria-labelledby="group-more">
        <div><span className="public-index-line" /><h2 id="group-more">{locale === "en" ? "More from the program" : "திட்டத்தின் மேலும் தகவல்கள்"}</h2></div>
        <div className="public-index-grid">{additional.map((item) =>
          <Link key={item.id} href={"/" + locale + "/pages/" + item.slug}><strong>{item.title}</strong><ArrowUpRight size={20} aria-hidden="true" /></Link>)}</div>
      </section>}
      {data?.next_cursor && <Link className="public-index-more" href={"?cursor=" + data.next_cursor}>{locale === "en" ? "More published pages" : "மேலும் வெளியிடப்பட்ட பக்கங்கள்"}<ArrowRight size={18} aria-hidden="true" /></Link>}
    </div>
  </main>;
}
