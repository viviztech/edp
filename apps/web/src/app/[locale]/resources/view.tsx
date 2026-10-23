import Link from "next/link";
import type { components } from "../../../lib/api-contracts";
import { ResourceCard, ResourceFilters, words, type Locale } from "../knowledge/content";

export default function PublicResources({ locale, data, failed, filters }: { locale: Locale;
  data: components["schemas"]["KnowledgeList"] | null; failed: boolean; filters: Record<string, string> }) {
  const t = words[locale];
  const next = new URLSearchParams(filters);
  if (data?.next_cursor) next.set("cursor", data.next_cursor);
  return <main id="main" className="program-main knowledge-main"><header className="program-heading"><div>
    <p className="eyebrow">K01</p><h1>{t.title}</h1><p>{t.intro}</p></div></header>
    <ResourceFilters locale={locale} initial={filters} />
    {failed ? <p role="status">{t.error}</p> : !data?.items.length ? <p>{t.empty}</p> : <section aria-label={t.title}>
      {data.items.map((item) => <ResourceCard key={item.id} item={item} locale={locale} />)}</section>}
    {data?.next_cursor && <Link href={`/${locale}/resources?${next}`}>{t.more}</Link>}
    <p><Link href={`/${locale}/account`}>{t.account}</Link></p>
  </main>;
}
