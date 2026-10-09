import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { isLocale, messages } from "../../lib/messages";
import Link from "next/link";
import { ArrowRight, ArrowUpRight } from "lucide-react";
import { buttonVariants } from "../../components/ui/button";
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
  return <main id="main" className="home-main">
    <section className="home-hero relative" aria-labelledby="home-title"><div className="home-hero-copy">
    <p className="eyebrow inline-flex items-center gap-2">{text.title}</p>
    <h1 id="home-title">{text.introduction}</h1>
    <p className="description">{text.description}</p><Link className={buttonVariants({ size: "lg", className: "home-primary-action" })} href={`/${locale}/account`}>{text.apply}<ArrowRight aria-hidden="true" /></Link></div><div className="home-hero-art" aria-hidden="true" /></section>
    <Card className="program-notice"><CardContent><span className="home-notice-dot" aria-hidden="true" /><span>{text.availability}</span></CardContent></Card>
    {navigation.length > 0 && <section className="information-grid" aria-labelledby="discover-heading">
      <div><p className="eyebrow">{text.discoverEyebrow}</p><h2 id="discover-heading">{text.discoverTitle}</h2></div>
      <div className="information-cards">
        {navigation.map((page) => <Card className="program-card" key={page.id}><CardContent><Link className="information-card" href={`/${locale}/pages/${page.slug}`}>
          <span>{page.title}</span><ArrowUpRight aria-hidden="true" size={20} />
        </Link></CardContent></Card>)}
      </div>
    </section>}
  </main>;
}
