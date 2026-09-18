import "server-only";
import { cache } from "react";
import type { components } from "./api-contracts";
export type PublicPage=components["schemas"]["PublicPage"];
export async function publicPages(locale:string,slug?:string,cursor?:string):Promise<Response|null> {
 const org=process.env.PUBLIC_ORGANIZATION_ID, api=process.env.API_INTERNAL_URL;
 if(!org||!/^[0-9a-f-]{36}$/i.test(org)||!api) return null;
 const query=new URLSearchParams({locale,limit:"25"});if(cursor)query.set("cursor",cursor);
 return fetch(api.replace(/\/$/,"")+`/api/v1/public/organizations/${org}/pages`+(slug?"/"+encodeURIComponent(slug):"")+"?"+query,{cache:"no-store",signal:AbortSignal.timeout(8000)});
}
export const publicPage=cache(async(locale:string,slug:string):Promise<PublicPage|null>=>{const r=await publicPages(locale,slug);if(!r||r.status===404)return null;if(!r.ok)throw new Error("Public content unavailable");return r.json();});
