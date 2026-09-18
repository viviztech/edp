import Link from "next/link";
import {notFound} from "next/navigation";
import {publicPages} from "../../../lib/public-pages";
import {cmsMessages} from "../../../lib/cms-messages";
import {isLocale} from "../../../lib/messages";
import type {components} from "../../../lib/api-contracts";
export const dynamic="force-dynamic";
export default async function Pages({params,searchParams}:{params:Promise<{locale:string}>;searchParams:Promise<{cursor?:string}>}) {
 const {locale}=await params;if(!isLocale(locale))notFound();const t=cmsMessages[locale];
 let data:components["schemas"]["PublicList"]|null=null;
 try{const r=await publicPages(locale,undefined,(await searchParams).cursor);if(r?.ok)data=await r.json();}catch{}
 return <main id="main"><h1>{t.pages}</h1>{!data?<p role="alert">{t.unavailable}</p>:<>{!data.items.length&&<p>{t.empty}</p>}<ul>{data.items.map(p=><li key={p.id}><Link href={`/${locale}/pages/${p.slug}`}>{p.title}</Link></li>)}</ul>{data.next_cursor&&<Link href={`?cursor=${data.next_cursor}`}>{t.more}</Link>}</>}<Link href={`/${locale}`}>{t.back}</Link></main>;
}
