import Link from "next/link";
import { notFound } from "next/navigation";
import { publicEditorial, type EditorialKind } from "../../../../lib/public-editorial";
import type { Metadata } from "next";
import { absoluteUrl } from "../../../../lib/site-url";
import { isLocale, messages } from "../../../../lib/messages";
import { editorialLabels, editorialEmpty } from "../../../../lib/editorial-copy";
const kinds:EditorialKind[]=["news","event","faq","testimonial"];
export const dynamic="force-dynamic";
export async function generateMetadata({params}:{params:Promise<{locale:string;kind:string}>}):Promise<Metadata>{const p=await params;return {title:p.kind,alternates:{canonical:absoluteUrl(`/${p.locale}/content/${p.kind}`),languages:{en:absoluteUrl(`/en/content/${p.kind}`),ta:absoluteUrl(`/ta/content/${p.kind}`)}}};}
export default async function EditorialList({params}:{params:Promise<{locale:string;kind:string}>}){const p=await params;if(!isLocale(p.locale)||!kinds.includes(p.kind as EditorialKind))notFound();const data=await publicEditorial(p.kind as EditorialKind,p.locale);return <main className="content-shell editorial-index"><p className="eyebrow">{messages[p.locale].title}</p><h1>{editorialLabels[p.locale][p.kind as EditorialKind]}</h1><div className="editorial-list">{data?.items.map(i=><Link className="information-card" key={i.id} href={`/${p.locale}/content/${p.kind}/${i.slug}`}><h2>{i.title}</h2>{i.starts_at&&<p className="content-date">{new Intl.DateTimeFormat(p.locale).format(new Date(i.starts_at))}</p>}<p>{i.body}</p></Link>)}</div>{!data?.items.length&&<p>{editorialEmpty[p.locale]}</p>}</main>}
