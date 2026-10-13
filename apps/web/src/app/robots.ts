import type { MetadataRoute } from "next";
import { absoluteUrl } from "../lib/site-url";
export const dynamic = "force-dynamic";
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: ["/en", "/ta"],
      disallow: [
        "/api/",
        "/en/demo",
        "/ta/demo",
        "/en/account",
        "/ta/account",
        "/en/admin",
        "/ta/admin",
        "/en/applications",
        "/ta/applications",
        "/en/participant",
        "/ta/participant",
        "/en/learning",
        "/ta/learning",
        "/en/mentoring",
        "/ta/mentoring",
        "/en/business-plans",
        "/ta/business-plans",
        "/en/business-plan",
        "/ta/business-plan",
        "/en/attendance",
        "/ta/attendance",
        "/en/businesses",
        "/ta/businesses",
      ],
    },
    sitemap: absoluteUrl("/sitemap.xml"),
  };
}
