import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { isLocale, messages } from "../../lib/messages";

export async function generateMetadata({ params }: { params: Promise<{locale: string}> }): Promise<Metadata> {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  return { title: messages[locale].title, description: messages[locale].description };
}

export default async function Home({ params }: { params: Promise<{locale: string}> }) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const text = messages[locale];
  return <main id="main">
    <p className="eyebrow">{text.title}</p>
    <h1>{text.introduction}</h1>
    <p className="description">{text.description}</p>
    <aside className="notice">{text.availability}</aside>
  </main>;
}
