import type { MetadataRoute } from "next";
import { absoluteUrl } from "../lib/site-url";
const locales=["en","ta"];
const kinds=["news","event","faq","testimonial"];
export default function sitemap(): MetadataRoute.Sitemap {
  const urls: MetadataRoute.Sitemap=[];
  for (const locale of locales) {
    urls.push({url:absoluteUrl(`/${locale}`),alternates:{languages:{en:absoluteUrl(`/en`),ta:absoluteUrl(`/ta`)}}});
    urls.push({url:absoluteUrl(`/${locale}/pages`),alternates:{languages:{en:absoluteUrl(`/en/pages`),ta:absoluteUrl(`/ta/pages`)}}});
    for (const kind of kinds) urls.push({url:absoluteUrl(`/${locale}/content/${kind}`),alternates:{languages:{en:absoluteUrl(`/en/content/${kind}`),ta:absoluteUrl(`/ta/content/${kind}`)}}});
  }
  return urls;
}
