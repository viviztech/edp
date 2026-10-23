import "server-only";
import { cache } from "react";
import { intakeId } from "./intake-context";
import { isLocale } from "./messages";
export type EditorialKind="news"|"event"|"faq"|"testimonial";
export type PublicEditorial={id:string;kind:EditorialKind;slug:string;locale:string;title:string;body:string;starts_at:string|null;ends_at:string|null;sort_order:number;state:"published";version:number;published_at:string|null};
type Batch={items:PublicEditorial[];next_cursor:string|null};
async function call(kind: EditorialKind, locale: string, slug?: string, cursor?: string) {
  if (!["news", "event", "faq", "testimonial"].includes(kind) || !isLocale(locale) || (cursor !== undefined && !intakeId(cursor))) throw new Error("Invalid public content query");
  if (slug !== undefined && !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) return null;
  const org = intakeId(process.env.PUBLIC_ORGANIZATION_ID), api = process.env.API_INTERNAL_URL;
  if (!org || !api) return null;
  const base = api.replace(/\/$/, "") + `/api/v1/public/organizations/${org}/editorial`;
  const query = new URLSearchParams({ locale });
  if (!slug) { query.set("kind", kind); query.set("limit", "25"); if (cursor) query.set("cursor", cursor); }
  const url = `${base}${slug ? `/${kind}/${encodeURIComponent(slug)}` : ""}?${query}`;
  const response = await fetch(url, { cache: "no-store", signal: AbortSignal.timeout(8000) });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error("Public content unavailable");
  return response.json();
}
export const publicEditorial = cache(async (kind: EditorialKind, locale: string, cursor?: string): Promise<Batch | null> => call(kind, locale, undefined, cursor));
export const publicEditorialItem = cache(async (kind: EditorialKind, slug: string, locale: string): Promise<PublicEditorial | null> => call(kind, locale, slug));
