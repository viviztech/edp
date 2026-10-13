import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Check,
  Compass,
  Lightbulb,
  MessageCircle,
  MoveUpRight,
  Plus,
  Sprout,
  Users,
} from "lucide-react";
import { JourneyExplorer } from "../../components/journey-explorer";
import { landingCopy } from "../../lib/landing-copy";
import { isLocale, messages } from "../../lib/messages";
import { absoluteUrl } from "../../lib/site-url";
import { launchCopy, publicLaunch } from "../../lib/public-launch";

const valueIcons = [BookOpen, MessageCircle, Users, Sprout];
const exploreIcons = [Compass, Users, BookOpen];

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  return {
    title: messages[locale].title,
    description: messages[locale].description,
    alternates: {
      canonical: absoluteUrl(`/${locale}`),
      languages: {
        en: absoluteUrl("/en"),
        ta: absoluteUrl("/ta"),
        "x-default": absoluteUrl("/en"),
      },
    },
    openGraph: {
      title: messages[locale].title,
      description: messages[locale].description,
      url: absoluteUrl(`/${locale}`),
      siteName: "CSJE EDP",
      locale: locale === "en" ? "en_IN" : "ta_IN",
      type: "website",
      images: [
        {
          url: "/images/entrepreneurs-hero.png",
          width: 1536,
          height: 1024,
          alt: landingCopy[locale].photoAlt,
        },
      ],
    },
  };
}

export default async function Home({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const copy = landingCopy[locale];
  const launch = publicLaunch();
  return (
    <main id="main" className="landing-main">
      <section
        className="public-hero public-container"
        aria-labelledby="home-title"
      >
        <div className="public-hero-copy">
          <p className="public-kicker">
            <span aria-hidden="true" />
            {copy.eyebrow}
          </p>
          <h1 id="home-title">
            {copy.headline.map((line, index) => (
              <span
                key={line}
                className={index === 2 ? "hero-emphasis" : undefined}
              >
                {line}
              </span>
            ))}
          </h1>
          <p className="public-hero-intro">{copy.intro}</p>
          <div className="public-actions">
            <Link
              className="public-button public-button-primary"
              href={launch.demo ? `/${locale}/demo` : `/${locale}/pages/about`}
            >
              {launch.demo ? launchCopy[locale].demo : copy.primary}
              <ArrowUpRight size={19} aria-hidden="true" />
            </Link>
            <a className="public-hero-secondary" href="#journey">
              <span>
                <ArrowDownRight size={19} aria-hidden="true" />
              </span>
              {copy.secondary}
            </a>
          </div>
          <div className="hero-small-note">
            <span aria-hidden="true" />
            <p>{messages[locale].availability}</p>
          </div>
        </div>
        <div className="public-hero-art">
          <div className="hero-photo-wrap">
            <Image
              src="/images/entrepreneurs-hero.png"
              alt={copy.photoAlt}
              fill
              sizes="(max-width: 760px) 110vw, (max-width: 1200px) 65vw, 800px"
              loading="eager"
              fetchPriority="high"
              className="hero-photo"
            />
          </div>
          <div className="hero-possibility-card">
            <div className="hero-card-title">
              <span className="hero-spark">
                <Lightbulb size={21} aria-hidden="true" />
              </span>
              <strong>{copy.photoNote}</strong>
            </div>
            <div className="hero-pathway" aria-hidden="true">
              <span>
                <Lightbulb size={19} />
                {copy.idea}
              </span>
              <i />
              <span>
                <Users size={19} />
                {copy.support}
              </span>
              <i />
              <span>
                <Sprout size={19} />
                {copy.future}
              </span>
            </div>
          </div>
          <div className="hero-growth-mark" aria-hidden="true">
            <MoveUpRight size={34} strokeWidth={1.4} />
          </div>
        </div>
      </section>
      <div className="public-value-strip public-container">
        {copy.values.map((value, index) => {
          const Icon = valueIcons[index];
          return (
            <div key={value}>
              <Icon size={23} strokeWidth={1.5} aria-hidden="true" />
              <span>{value}</span>
            </div>
          );
        })}
      </div>
      <section
        className="public-section public-container support-section"
        aria-labelledby="support-title"
      >
        <div className="public-section-heading">
          <div>
            <p className="public-kicker">{copy.supportEyebrow}</p>
            <h2 id="support-title">{copy.supportTitle}</h2>
          </div>
          <p>{copy.supportIntro}</p>
        </div>
        <div className="support-grid">
          {copy.features.map((feature, index) => (
            <article
              className={`support-card support-card-${index}`}
              key={feature.path}
            >
              <div className="support-card-art" aria-hidden="true">
                {index === 0 ? (
                  <div className="learning-art">
                    <div className="learning-art-header">
                      <BookOpen size={25} strokeWidth={1.4} />
                      <span>EDP</span>
                    </div>
                    {copy.lessonLabels.map((label, lesson) => (
                      <div className="learning-art-row" key={label}>
                        <span>
                          {lesson === 2 ? (
                            <ArrowUpRight size={14} />
                          ) : (
                            <Check size={13} />
                          )}
                        </span>
                        <strong>{label}</strong>
                        <i />
                      </div>
                    ))}
                  </div>
                ) : index === 1 ? (
                  <div className="mentoring-art">
                    <div className="conversation conversation-question">
                      <span>
                        <MessageCircle size={20} />
                      </span>
                      {copy.conversation[0]}
                    </div>
                    <div className="conversation conversation-answer">
                      {copy.conversation[1]}
                      <span>
                        <Users size={20} />
                      </span>
                    </div>
                    <div className="conversation-dots">
                      <i />
                      <i />
                      <i />
                    </div>
                  </div>
                ) : (
                  <div className="growth-art">
                    {copy.growthLabels.map((label, step) => (
                      <div
                        className={`growth-art-step growth-art-step-${step}`}
                        key={label}
                      >
                        <span>
                          {step === 0 ? (
                            <Lightbulb size={22} />
                          ) : step === 1 ? (
                            <BookOpen size={22} />
                          ) : (
                            <Sprout size={25} />
                          )}
                        </span>
                        <small>{label}</small>
                      </div>
                    ))}
                    <MoveUpRight
                      className="growth-art-arrow"
                      size={58}
                      strokeWidth={1.1}
                    />
                  </div>
                )}
              </div>
              <h3>{feature.title}</h3>
              <p>{feature.body}</p>
              <Link href={`/${locale}${feature.path}`}>
                {feature.action}
                <ArrowUpRight size={19} aria-hidden="true" />
              </Link>
            </article>
          ))}
        </div>
        <p className="support-availability">{copy.featureNote}</p>
      </section>
      <section
        id="journey"
        className="public-journey-section"
        aria-labelledby="journey-title"
      >
        <div className="public-container">
          <div className="public-section-heading">
            <div>
              <p className="public-kicker">{copy.journeyEyebrow}</p>
              <h2 id="journey-title">{copy.journeyTitle}</h2>
            </div>
            <p>{copy.journeyIntro}</p>
          </div>
          <JourneyExplorer
            locale={locale}
            label={copy.journeyLabel}
            stages={copy.stages}
          />
        </div>
      </section>
      <section
        className="public-section public-container explore-section"
        aria-labelledby="explore-title"
      >
        <div className="public-section-heading">
          <div>
            <p className="public-kicker">{copy.exploreEyebrow}</p>
            <h2 id="explore-title">{copy.exploreTitle}</h2>
          </div>
          <Link className="public-text-link" href={`/${locale}/pages`}>
            {copy.exploreAll}
            <ArrowRight size={18} aria-hidden="true" />
          </Link>
        </div>
        <div className="explore-grid">
          {copy.exploreCards.map((card, index) => {
            const Icon = exploreIcons[index];
            return (
              <Link
                href={`/${locale}${card.path}`}
                className="explore-card"
                key={card.path}
              >
                <span className="explore-icon">
                  <Icon size={27} strokeWidth={1.4} aria-hidden="true" />
                </span>
                <ArrowUpRight
                  className="explore-arrow"
                  size={20}
                  aria-hidden="true"
                />
                <h3>{card.title}</h3>
                <p>{card.body}</p>
              </Link>
            );
          })}
        </div>
      </section>
      <section
        className="public-faq public-container"
        aria-labelledby="faq-title"
      >
        <div className="faq-heading">
          <p className="public-kicker">{copy.faqEyebrow}</p>
          <h2 id="faq-title">{copy.faqTitle}</h2>
          <p>{copy.faqHelp}</p>
          <Link className="public-text-link" href={`/${locale}/pages/contact`}>
            {copy.faqContact}
            <ArrowUpRight size={18} aria-hidden="true" />
          </Link>
        </div>
        <div className="faq-list">
          {copy.faqs.map((faq) => (
            <details key={faq.question}>
              <summary>
                <span>{faq.question}</span>
                <Plus size={21} aria-hidden="true" />
              </summary>
              <p>{faq.answer}</p>
            </details>
          ))}
        </div>
      </section>
      <section
        className="public-closing public-container"
        aria-labelledby="closing-title"
      >
        <div className="closing-orbit" aria-hidden="true">
          <Sprout size={65} strokeWidth={1} />
        </div>
        <div className="closing-copy">
          <p className="public-kicker">{copy.closingEyebrow}</p>
          <h2 id="closing-title">{copy.closingTitle}</h2>
          <p>{copy.closingBody}</p>
          <div className="public-actions">
            <Link
              className="public-button public-button-light"
              href={`/${locale}/tools/idea-planner`}
            >
              {launchCopy[locale].resourceAction}
              <ArrowUpRight size={19} aria-hidden="true" />
            </Link>
            <Link className="closing-account" href={`/${locale}/pages/apply`}>
              {locale === "en"
                ? "Explore participation"
                : "பங்கேற்பை அறியுங்கள்"}
              <ArrowRight size={18} aria-hidden="true" />
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
