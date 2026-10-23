import Link from "next/link";
import { ArrowLeft, ArrowUpRight } from "lucide-react";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { publicEditorial, type EditorialKind } from "../../../../lib/public-editorial";
import { absoluteUrl } from "../../../../lib/site-url";
import { isLocale, messages } from "../../../../lib/messages";
import { editorialLabels, editorialEmpty, editorialIntroductions } from "../../../../lib/editorial-copy";
import { intakeId, type IntakeSearch } from "../../../../lib/intake-context";

const kinds: EditorialKind[] = ["news", "event", "faq", "testimonial"];
type Props = { params: Promise<{ locale: string; kind: string }>; searchParams?: Promise<IntakeSearch> };
export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, kind } = await params;
  if (!isLocale(locale) || !kinds.includes(kind as EditorialKind)) return {};
  return {
    title: editorialLabels[locale][kind as EditorialKind],
    description: editorialIntroductions[locale][kind as EditorialKind],
    alternates: {
      canonical: absoluteUrl("/" + locale + "/content/" + kind),
      languages: { en: absoluteUrl("/en/content/" + kind), ta: absoluteUrl("/ta/content/" + kind) },
    },
  };
}

export default async function EditorialList({ params, searchParams }: Props) {
  const { locale, kind } = await params;
  if (!isLocale(locale) || !kinds.includes(kind as EditorialKind)) notFound();
  const selected = kind as EditorialKind;
  const input = searchParams ? await searchParams : {};
  if (Object.keys(input).some(key => key !== "cursor") || (input.cursor !== undefined && !intakeId(input.cursor))) notFound();
  const cursor = intakeId(input.cursor);
  let data: Awaited<ReturnType<typeof publicEditorial>> = null;
  let unavailable = false;
  try { data = await publicEditorial(selected, locale, cursor); } catch { unavailable = true; }
  const next = intakeId(data?.next_cursor);
  return <main id="main" tabIndex={-1} className="editorial-public">
    <div className="editorial-public-shell">
      <p className="public-eyebrow">{messages[locale].title}</p>
      <h1>{editorialLabels[locale][selected]}</h1>
      <p className="editorial-public-intro">{editorialIntroductions[locale][selected]}</p>
      {unavailable ? <p role="alert">{locale === "en" ? "Content could not be loaded. Please try again." : "உள்ளடக்கத்தை ஏற்ற முடியவில்லை. மீண்டும் முயலவும்."}</p> : data?.items.length ? <div className="editorial-public-grid">{data.items.map((item) =>
        <Link key={item.id} href={"/" + locale + "/content/" + kind + "/" + encodeURIComponent(item.slug)}>
          <span>{item.starts_at && new Intl.DateTimeFormat(locale).format(new Date(item.starts_at))}</span>
          <h2>{item.title}</h2>
          <p>{item.body}</p>
          <ArrowUpRight size={20} aria-hidden="true" />
        </Link>)}</div> : <div className="editorial-public-empty">{editorialEmpty[locale]}</div>}
      <nav className="actions" aria-label={locale === "en" ? "Content pagination" : "உள்ளடக்கப் பக்கங்கள்"}>
        {cursor && <Link href={`/${locale}/content/${kind}`}>{locale === "en" ? "First page" : "முதல் பக்கம்"}</Link>}
        {next && <Link href={`/${locale}/content/${kind}?${new URLSearchParams({ cursor: next })}`}>{locale === "en" ? "Next page" : "அடுத்த பக்கம்"}</Link>}
      </nav>
      <Link className="editorial-public-back" href={"/" + locale + "/pages"}><ArrowLeft size={18} aria-hidden="true" />{locale === "en" ? "All pages" : "அனைத்து பக்கங்களும்"}</Link>
    </div>
  </main>;
}
