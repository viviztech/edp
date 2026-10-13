import type { MetadataRoute } from "next";
import { absoluteUrl } from "../lib/site-url";
import { launchPages } from "../lib/launch-public-pages";
const locales = ["en", "ta"];
const kinds = ["faq"];
export const dynamic = "force-dynamic";
export default function sitemap(): MetadataRoute.Sitemap {
  const urls: MetadataRoute.Sitemap = [];
  for (const locale of locales) {
    urls.push({
      url: absoluteUrl(`/${locale}`),
      alternates: {
        languages: { en: absoluteUrl(`/en`), ta: absoluteUrl(`/ta`) },
      },
    });
    urls.push({
      url: absoluteUrl(`/${locale}/pages`),
      alternates: {
        languages: {
          en: absoluteUrl(`/en/pages`),
          ta: absoluteUrl(`/ta/pages`),
        },
      },
    });
    for (const page of launchPages)
      urls.push({
        url: absoluteUrl(`/${locale}/pages/${page.slug}`),
        alternates: {
          languages: {
            en: absoluteUrl(`/en/pages/${page.slug}`),
            ta: absoluteUrl(`/ta/pages/${page.slug}`),
          },
        },
      });
    urls.push({
      url: absoluteUrl(`/${locale}/tools/idea-planner`),
      alternates: {
        languages: {
          en: absoluteUrl("/en/tools/idea-planner"),
          ta: absoluteUrl("/ta/tools/idea-planner"),
        },
      },
    });
    for (const kind of kinds)
      urls.push({
        url: absoluteUrl(`/${locale}/content/${kind}`),
        alternates: {
          languages: {
            en: absoluteUrl(`/en/content/${kind}`),
            ta: absoluteUrl(`/ta/content/${kind}`),
          },
        },
      });
  }
  return urls;
}
