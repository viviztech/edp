import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import type { components } from "../../../lib/api-contracts";
import { authMessages } from "../../../lib/auth-messages";
import { isLocale } from "../../../lib/messages";
import { serverApi } from "../../../lib/server-api";
import Audit from "./view";
import { StaffModuleNav } from "../../../components/staff-module-nav";

export default async function AdminShell({ params, searchParams }: {
  params: Promise<{ locale: string }>; searchParams: Promise<{ organization?: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const text = authMessages[locale];
  let response: Response;
  try { response = await serverApi("/auth/me"); }
  catch { return <main id="main"><p role="alert">{text.unavailable}</p></main>; }
  if (response.status === 401) redirect("/" + locale + "/account");
  if (!response.ok) return <main id="main"><p role="alert">{text.error}</p></main>;
  const profile: components["schemas"]["Profile"] = await response.json();
  const selected = (await searchParams).organization;
  const grant = profile.grants.find(item => (!selected || item.organization_id === selected) && item.permissions.includes("system.access"));
  if (!grant) return <main id="main"><p>{text.denied}</p><Link href={"/" + locale + "/account"}>{text.back}</Link></main>;
  let access: Response;
  try { access = await serverApi("/system/organizations/" + grant.organization_id + "/access"); }
  catch { return <main id="main"><p role="alert">{text.unavailable}</p></main>; }
  if (!access.ok) return <main id="main"><p>{text.denied}</p></main>;
  return <main id="main" className="admin-home">
    <div className="admin-home-heading">
      <div><p className="eyebrow">{grant.organization_name}</p><h1>{text.staff}</h1></div>
      <Link href={"/" + locale + "/account"}>{text.back}</Link>
    </div>
    <StaffModuleNav locale={locale} organization={grant.organization_id} permissions={grant.permissions} variant="tiles" />
    {grant.permissions.includes("audit.view") && <div className="admin-audit"><Audit organization={grant.organization_id} text={text} /></div>}
  </main>;
}
