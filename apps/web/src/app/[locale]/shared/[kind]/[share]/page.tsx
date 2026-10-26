import { notFound } from "next/navigation";
import type { components } from "../../../../../lib/api-contracts";
import { toolsCopy } from "../../../../../lib/business-tools-copy";
import { isLocale } from "../../../../../lib/messages";
import "../../../business-tools/tools.css";

export const dynamic = "force-dynamic";
export const metadata = { robots: { index: false, follow: false } };

export default async function SharedBusinessPage({ params, searchParams }: {
  params: Promise<{ locale: string; kind: string; share: string }>;
  searchParams: Promise<{ offset?: string }>;
}) {
  const { locale, kind, share } = await params;
  if (!isLocale(locale) || !["card", "catalogue"].includes(kind) || !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(share)) notFound();
  const t = toolsCopy[locale]; const offsetValue = (await searchParams).offset ?? "0";
  if (!/^(?:0|[1-9][0-9]{0,3}|10000)$/.test(offsetValue)) notFound();
  const offset = Number(offsetValue); let response: Response;
  try {
    const api = process.env.API_INTERNAL_URL; if (!api) throw new Error("missing_configuration");
    response = await fetch(`${api.replace(/\/$/, "")}/api/v1/public/business-tools/${kind === "card" ? "cards" : "catalogues"}/${share}${kind === "catalogue" ? `?limit=25&offset=${offset}` : ""}`, { cache: "no-store", signal: AbortSignal.timeout(8000) });
  } catch { response = new Response(null, { status: 503 }); }
  if (response.status === 404) notFound();
  if (!response.ok) return <main id="main" tabIndex={-1} className="tools-public"><h1>{kind === "card" ? t.card : t.catalogue}</h1><p>{t.unavailable}</p></main>;
  if (kind === "card") {
    const card = await response.json() as components["schemas"]["PublicCard"];
    return <main id="main" tabIndex={-1} className="tools-public"><article className="tools-card"><h1>{locale === "ta" ? card.name_ta || card.name_en : card.name_en}</h1>
      <p>{locale === "ta" ? card.tagline_ta : card.tagline_en}</p><p>{locale === "ta" ? card.description_ta : card.description_en}</p>
      <p>{card.phone}</p><p>{card.email}</p><p>{locale === "ta" ? card.address_ta : card.address_en}</p>
      {card.website.startsWith("https://") && <a href={card.website} rel="noreferrer">{card.website}</a>}</article></main>;
  }
  const catalogue = await response.json() as components["schemas"]["PublicCatalogue"];
  const path = `/${locale}/shared/catalogue/${share}`;
  return <main id="main" tabIndex={-1} className="tools-public"><h1>{t.catalogue}</h1><ul>{catalogue.items.map((item, index) => <li key={index}>
    <h2>{locale === "ta" ? item.name_ta || item.name_en : item.name_en}</h2><p>{locale === "ta" ? item.description_ta : item.description_en}</p>
    {item.price !== null && item.price !== undefined && <p>{item.price} {item.currency}</p>}</li>)}</ul>
    {!catalogue.items.length && <p>{t.noItems}</p>}<nav aria-label={t.catalogue}>{offset > 0 && <a href={`${path}?offset=${Math.max(0, offset - 25)}`}>{t.previous}</a>} {catalogue.items.length === 25 && offset < 10000 && <a href={`${path}?offset=${offset + 25}`}>{t.next}</a>}</nav>
  </main>;
}
