import type { Locale } from "./messages";
import { launchPages } from "./launch-public-pages";

export type StarterPage = {
  title: string;
  eyebrow: string;
  intro: string;
  sections: readonly { heading: string; body: string }[];
  note?: string;
  next?: { label: string; path: string };
};

export const starterPages = launchPages;
export const starterPage = (
  locale: Locale,
  slug: string,
): StarterPage | undefined =>
  launchPages.find((page) => page.slug === slug)?.[locale];
export const starterPageList = (locale: Locale) =>
  launchPages.map((page) => ({
    slug: page.slug,
    title: page[locale].title,
    group: page.group,
  }));

export const publicNavLabels = {
  en: {
    program: "The program",
    support: "Explore",
    updates: "Updates",
    home: "Home",
    contact: "Contact",
    apply: "Apply",
    account: "Account",
    all: "All pages",
    news: "News",
    events: "Events",
    faq: "FAQ",
    stories: "Stories",
  },
  ta: {
    program: "திட்டம்",
    support: "ஆராயுங்கள்",
    updates: "புதியவை",
    home: "முகப்பு",
    contact: "தொடர்பு",
    apply: "விண்ணப்பம்",
    account: "கணக்கு",
    all: "அனைத்து பக்கங்களும்",
    news: "செய்திகள்",
    events: "நிகழ்வுகள்",
    faq: "கேள்வி பதில்கள்",
    stories: "கதைகள்",
  },
} as const;
