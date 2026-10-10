import Link from "next/link";
import { ArrowLeft, ArrowUpRight } from "lucide-react";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { publicEditorial, type EditorialKind } from "../../../../lib/public-editorial";
import { absoluteUrl } from "../../../../lib/site-url";
import { isLocale, messages } from "../../../../lib/messages";
import { editorialLabels, editorialEmpty, editorialIntroductions } from "../../../../lib/editorial-copy";

const kinds: EditorialKind[] = ["news", "event", "faq", "testimonial"];
type Props = { params: Promise<{ locale: string; kind: string }> };
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

export default async function EditorialList({ params }: Props) {
  const { locale, kind } = await params;
  if (!isLocale(locale) || !kinds.includes(kind as EditorialKind)) notFound();
  const selected = kind as EditorialKind;
  let data: Awaited<ReturnType<typeof publicEditorial>> = null;
  try { data = await publicEditorial(selected, locale); } catch {}
  return <main id="main" className="editorial-public">
    <div className="editorial-public-shell">
      <p className="public-eyebrow">{messages[locale].title}</p>
      <h1>{editorialLabels[locale][selected]}</h1>
      <p className="editorial-public-intro">{editorialIntroductions[locale][selected]}</p>
      {data?.items.length ? <div className="editorial-public-grid">{data.items.map((item) =>
        <Link key={item.id} href={"/" + locale + "/content/" + kind + "/" + item.slug}>
          <span>{item.starts_at && new Intl.DateTimeFormat(locale).format(new Date(item.starts_at))}</span>
          <h2>{item.title}</h2>
          <p>{item.body}</p>
          <ArrowUpRight size={20} aria-hidden="true" />
        </Link>)}</div> : <div className="editorial-public-empty">{editorialEmpty[locale]}</div>}
      <Link className="editorial-public-back" href={"/" + locale + "/pages"}><ArrowLeft size={18} aria-hidden="true" />{locale === "en" ? "All pages" : "அனைத்து பக்கங்களும்"}</Link>
    </div>
  </main>;
}
