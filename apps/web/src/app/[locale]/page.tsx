import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { isLocale, messages } from "../../lib/messages";
import Link from "next/link";
import { Card, CardContent } from "../../components/ui/card";
import { publicNavigation } from "../../lib/public-navigation";

export async function generateMetadata({ params }: { params: Promise<{locale: string}> }): Promise<Metadata> {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  return { title: messages[locale].title, description: messages[locale].description };
}

export default async function Home({ params }: { params: Promise<{locale: string}> }) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const text = messages[locale];
  const navigation = await publicNavigation(locale);
  return <main id="main">
    <p className="eyebrow">{text.title}</p>
    <h1>{text.introduction}</h1>
    <p className="description">{text.description}</p>
    <Card className="program-notice"><CardContent><span>{text.availability}</span><Link className="program-cta" href={`/${locale}/account`}>{text.apply}</Link></CardContent></Card>
    {navigation.length > 0 && <section className="information-grid" aria-labelledby="discover-heading">
      <div><p className="eyebrow">{text.discoverEyebrow}</p><h2 id="discover-heading">{text.discoverTitle}</h2></div>
      <div className="information-cards">
        {navigation.map((page) => <Card className="program-card" key={page.id}><CardContent><Link className="information-card" href={`/${locale}/pages/${page.slug}`}>
          <span>{page.title}</span><span aria-hidden="true">-&gt;</span>
        </Link></CardContent></Card>)}
      </div>
    </section>}
  </main>;
}
