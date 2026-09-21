import { notFound } from "next/navigation";
import { publicEditorialItem, type EditorialKind } from "../../../../../lib/public-editorial";
import type { Metadata } from "next";
import { absoluteUrl } from "../../../../../lib/site-url";
import { isLocale } from "../../../../../lib/messages";
import { editorialLabels } from "../../../../../lib/editorial-copy";
const kinds:EditorialKind[]=["news","event","faq","testimonial"];
export const dynamic="force-dynamic";
export async function generateMetadata({params}:{params:Promise<{locale:string;kind:string;slug:string}>}):Promise<Metadata>{const p=await params;const item=await publicEditorialItem(p.kind as EditorialKind,p.slug,p.locale);return {title:item?.title??p.kind,description:item?.body?.slice(0,160),alternates:{canonical:absoluteUrl(`/${p.locale}/content/${p.kind}/${p.slug}`),languages:{en:absoluteUrl(`/en/content/${p.kind}/${p.slug}`),ta:absoluteUrl(`/ta/content/${p.kind}/${p.slug}`)}}};}
export default async function EditorialDetail({params}:{params:Promise<{locale:string;kind:string;slug:string}>}){const p=await params;if(!isLocale(p.locale)||!kinds.includes(p.kind as EditorialKind))notFound();const item=await publicEditorialItem(p.kind as EditorialKind,p.slug,p.locale);if(!item)notFound();return <main className="content-shell"><p className="eyebrow">{editorialLabels[p.locale][item.kind]}</p><h1>{item.title}</h1>{item.starts_at&&<p className="content-date">{new Intl.DateTimeFormat(p.locale).format(new Date(item.starts_at))}</p>}<p className="content-body">{item.body}</p></main>}
