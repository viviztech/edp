import { notFound, redirect } from "next/navigation";
import type { components } from "../../../../lib/api-contracts";
import { isLocale } from "../../../../lib/messages";
import { cmsMessages } from "../../../../lib/cms-messages";
import { serverApi } from "../../../../lib/server-api";
import Editor from "./view";
import { StaffModuleNav } from "../../../../components/staff-module-nav";
import "./workspace.css";
export const metadata = {robots:{index:false,follow:false}};
export default async function Cms({params,searchParams}:{params:Promise<{locale:string}>;searchParams:Promise<{organization?:string}>}) {
 const {locale}=await params; if(!isLocale(locale)) notFound(); const t=cmsMessages[locale];
 let response:Response; try {response=await serverApi("/auth/me");} catch {return <main id="main"><p role="alert">{t.error}</p></main>;}
 if(response.status===401) redirect(`/${locale}/account`);
 if(!response.ok) return <main id="main"><p role="alert">{t.error}</p></main>;
 const profile:components["schemas"]["Profile"]=await response.json(); const org=(await searchParams).organization;
 const grants=profile.grants.filter(g=>g.permissions.includes("cms.page.view")); const grant=grants.find(g=>!org||g.organization_id===org);
 if(!grant) return <main id="main"><p>{t.unavailable}</p></main>;
 return <main id="main" className="cms-main"><div className="cms-page-heading"><div><p className="cms-heading-kicker">{grant.organization_name}</p><h1>{t.workspace}</h1><p>{locale === "ta" ? "உங்கள் இணையதளப் பக்கங்களை எழுதி, மதிப்பாய்வு செய்து வெளியிடுங்கள்." : "Write, review and publish your website pages."}</p></div></div>
 {grants.length>1&&<nav className="cms-organization-switch" aria-label={locale === "ta" ? "நிறுவனத்தைத் தேர்ந்தெடுக்கவும்" : "Choose organization"}>{grants.map(g=><a aria-current={g.organization_id===grant.organization_id?"true":undefined} key={g.organization_id} href={`?organization=${g.organization_id}`}>{g.organization_name}</a>)}</nav>}
 <StaffModuleNav locale={locale} organization={grant.organization_id} permissions={grant.permissions} active="pages" />
 <Editor key={grant.organization_id} org={grant.organization_id} permissions={grant.permissions} locale={locale}/></main>;
}
