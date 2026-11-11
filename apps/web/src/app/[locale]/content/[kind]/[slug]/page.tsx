import { notFound } from "next/navigation";
import { publicEditorialItem, type EditorialKind } from "../../../../../lib/public-editorial";
import type { Metadata } from "next";
import { absoluteUrl } from "../../../../../lib/site-url";
import { isLocale } from "../../../../../lib/messages";
import { editorialLabels } from "../../../../../lib/editorial-copy";
import Link from "next/link";
import { ArrowLeft, CalendarDays } from "lucide-react";
import { Card, CardContent } from "../../../../../components/ui/card";
import "./editorial-detail.css";
const kinds:EditorialKind[]=["news","event","faq","testimonial"];
export const dynamic="force-dynamic";
export async function generateMetadata({params}:{params:Promise<{locale:string;kind:string;slug:string}>}):Promise<Metadata>{const p=await params;const item=await publicEditorialItem(p.kind as EditorialKind,p.slug,p.locale);return {title:item?.title??p.kind,description:item?.body?.slice(0,160),alternates:{canonical:absoluteUrl(`/${p.locale}/content/${p.kind}/${p.slug}`),languages:{en:absoluteUrl(`/en/content/${p.kind}/${p.slug}`),ta:absoluteUrl(`/ta/content/${p.kind}/${p.slug}`)}}};}
export default async function EditorialDetail({params}:{params:Promise<{locale:string;kind:string;slug:string}>}) {
  const p = await params;
  if (!isLocale(p.locale) || !kinds.includes(p.kind as EditorialKind)) notFound();
  const item = await publicEditorialItem(p.kind as EditorialKind, p.slug, p.locale);
  if (!item) notFound();
  return <main id="main" className="editorial-detail">
    <div className="editorial-detail-inner">
      <Link className="editorial-detail-back" href={`/${p.locale}/content/${p.kind}`}>
        <ArrowLeft size={17} aria-hidden="true" />{p.locale === "ta" ? "பட்டியலுக்குத் திரும்பு" : "Back to list"}
      </Link>
      <Card className="editorial-detail-card"><CardContent>
        <article>
          <p className="editorial-detail-kicker">{editorialLabels[p.locale][item.kind]}</p>
          <h1>{item.title}</h1>
          {item.starts_at && <p className="editorial-detail-date"><CalendarDays size={17} aria-hidden="true" /><time dateTime={item.starts_at}>{new Intl.DateTimeFormat(p.locale, { dateStyle: "long" }).format(new Date(item.starts_at))}</time></p>}
          <div className="editorial-detail-body">{item.body}</div>
        </article>
      </CardContent></Card>
    </div>
  </main>;
}
