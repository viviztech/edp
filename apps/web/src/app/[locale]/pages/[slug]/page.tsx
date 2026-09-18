import Link from "next/link";
import {notFound} from "next/navigation";
import type {Metadata} from "next";
import {publicPage} from "../../../../lib/public-pages";
import {cmsMessages} from "../../../../lib/cms-messages";
import {isLocale} from "../../../../lib/messages";
type Props={params:Promise<{locale:string;slug:string}>};
export const dynamic="force-dynamic";
export async function generateMetadata({params}:Props):Promise<Metadata>{
 const {locale,slug}=await params;if(!isLocale(locale))return {};
 const page=await publicPage(locale,slug);if(!page)return {robots:{index:false,follow:false}};
 const origin=process.env.WEB_ORIGIN;const other=locale==="en"?"ta":"en";const counterpart=await publicPage(other,slug);
 return {title:page.seo_title||page.title,description:page.seo_description||undefined,alternates:origin?{canonical:`${origin}/${locale}/pages/${slug}`,languages:{[locale]:`${origin}/${locale}/pages/${slug}`,...(counterpart?{[other]:`${origin}/${other}/pages/${slug}`}:{})}}:undefined};
}
export default async function Page({params}:Props){const {locale,slug}=await params;if(!isLocale(locale))notFound();const page=await publicPage(locale,slug);if(!page)notFound();return <main id="main"><article><h1>{page.title}</h1><div className="cms-body">{page.body}</div></article><p><Link href={`/${locale}/pages`}>{cmsMessages[locale].back}</Link></p></main>;}
