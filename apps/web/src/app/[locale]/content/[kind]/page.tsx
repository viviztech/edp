import Link from "next/link";
import { notFound } from "next/navigation";
import { publicEditorial, type EditorialKind } from "../../../../lib/public-editorial";
const kinds:EditorialKind[]=["news","event","faq","testimonial"];
export const dynamic="force-dynamic";
export default async function EditorialList({params}:{params:Promise<{locale:string;kind:string}>}){const p=await params;if(!kinds.includes(p.kind as EditorialKind))notFound();const data=await publicEditorial(p.kind as EditorialKind,p.locale);return <main className="content-shell"><p className="eyebrow">{p.kind}</p><h1>{p.kind}</h1><div className="information-grid">{data?.items.map(i=><Link className="information-card" key={i.id} href={`/${p.locale}/content/${p.kind}/${i.slug}`}><h2>{i.title}</h2>{i.starts_at&&<p className="content-date">{new Intl.DateTimeFormat(p.locale).format(new Date(i.starts_at))}</p>}<p>{i.body}</p></Link>)}</div>{!data?.items.length&&<p>No published content yet.</p>}</main>}
