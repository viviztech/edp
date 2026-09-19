import { notFound } from "next/navigation";
import { publicEditorialItem, type EditorialKind } from "../../../../../lib/public-editorial";
const kinds:EditorialKind[]=["news","event","faq","testimonial"];
export const dynamic="force-dynamic";
export default async function EditorialDetail({params}:{params:Promise<{locale:string;kind:string;slug:string}>}){const p=await params;if(!kinds.includes(p.kind as EditorialKind))notFound();const item=await publicEditorialItem(p.kind as EditorialKind,p.slug,p.locale);if(!item)notFound();return <main className="content-shell"><p className="eyebrow">{item.kind}</p><h1>{item.title}</h1>{item.starts_at&&<p className="content-date">{new Intl.DateTimeFormat(p.locale).format(new Date(item.starts_at))}</p>}<p className="content-body">{item.body}</p></main>}
