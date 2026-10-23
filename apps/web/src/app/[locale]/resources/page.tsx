import { notFound } from "next/navigation";
import type { components } from "../../../lib/api-contracts";
import { knowledgeQuery } from "../../../lib/knowledge-security";
import { isLocale } from "../../../lib/messages";
import { words } from "../knowledge/content";
import PublicResources from "./view";
import "../knowledge/knowledge.css";

export const dynamic = "force-dynamic";
type Props = { params: Promise<{ locale: string }>; searchParams: Promise<Record<string, string | string[] | undefined>> };
export async function generateMetadata({ params }: Props) {
  const { locale } = await params;
  return isLocale(locale) ? { title: words[locale].title, description: words[locale].intro } : {};
}

export default async function ResourcesPage({ params, searchParams }: Props) {
  const { locale } = await params; if (!isLocale(locale)) notFound();
  const input = await searchParams; const filters: Record<string, string> = {};
  let invalid = false;
  for (const [key, value] of Object.entries(input)) {
    if (!["q", "kind", "sector", "geography", "tag", "availability", "cursor"].includes(key)) invalid = true;
    if (Array.isArray(value)) { invalid = true; continue; }
    if (value && value.trim()) filters[key] = value.trim();
  }
  // The URL cannot select a different content language or organization.
  if ("locale" in filters || "state" in filters) invalid = true;
  const query = knowledgeQuery(new URLSearchParams({ ...filters, locale, limit: "25" }));
  const org = process.env.PUBLIC_ORGANIZATION_ID; const api = process.env.API_INTERNAL_URL;
  let data: components["schemas"]["KnowledgeList"] | null = null; let failed = invalid || query === null;
  if (!failed && org && /^[0-9a-f-]{36}$/i.test(org) && api) {
    try {
      const response = await fetch(`${api.replace(/\/$/, "")}/api/v1/public/organizations/${org}/knowledge?${query}`, {
        cache: "no-store", signal: AbortSignal.timeout(8000),
      });
      if (!response.ok) failed = true; else data = await response.json() as components["schemas"]["KnowledgeList"];
    } catch { failed = true; }
  }
  return <PublicResources locale={locale} data={data} failed={failed} filters={filters} />;
}
