import "server-only";
import { cache } from "react";
export type EditorialKind="news"|"event"|"faq"|"testimonial";
export type PublicEditorial={id:string;kind:EditorialKind;slug:string;locale:string;title:string;body:string;starts_at:string|null;ends_at:string|null;sort_order:number;state:"published";version:number;published_at:string|null};
type Batch={items:PublicEditorial[];next_cursor:string|null};
async function call(kind:EditorialKind,locale:string,slug?:string){const org=process.env.PUBLIC_ORGANIZATION_ID,api=process.env.API_INTERNAL_URL;if(!org||!/^[0-9a-f-]{36}$/i.test(org)||!api)return null;const base=api.replace(/\/$/,"")+`/api/v1/public/organizations/${org}/editorial`;const url=slug?`${base}/${kind}/${encodeURIComponent(slug)}?locale=${locale}`:`${base}?kind=${kind}&locale=${locale}&limit=25`;const r=await fetch(url,{cache:"no-store",signal:AbortSignal.timeout(8000)});if(r.status===404)return null;if(!r.ok)throw new Error("Public content unavailable");return r.json();}
export const publicEditorial=cache(async(kind:EditorialKind,locale:string):Promise<Batch|null>=>call(kind,locale));
export const publicEditorialItem=cache(async(kind:EditorialKind,slug:string,locale:string):Promise<PublicEditorial|null>=>call(kind,locale,slug));
