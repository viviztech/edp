import Link from "next/link";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { IdeaPlanner } from "../../../../components/idea-planner";
import { isLocale } from "../../../../lib/messages";
import { launchCopy } from "../../../../lib/public-launch";
import { absoluteUrl } from "../../../../lib/site-url";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  if (!isLocale(locale)) return {};
  return {
    title: launchCopy[locale].planner,
    description: launchCopy[locale].resourceIntro,
    alternates: {
      canonical: absoluteUrl(`/${locale}/tools/idea-planner`),
      languages: {
        en: absoluteUrl("/en/tools/idea-planner"),
        ta: absoluteUrl("/ta/tools/idea-planner"),
      },
    },
  };
}

export default async function PlannerPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  return (
    <main id="main" className="planner-main">
      <div className="planner-shell">
        <Link className="public-text-link" href={`/${locale}/pages/resources`}>
          {locale === "en" ? "Resources" : "வளங்கள்"}
        </Link>
        <p className="public-kicker">CSJE / EDP</p>
        <h1>{launchCopy[locale].resourceTitle}</h1>
        <p className="public-intro">{launchCopy[locale].resourceIntro}</p>
        <IdeaPlanner locale={locale} />
      </div>
    </main>
  );
}
