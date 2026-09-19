import type { MetadataRoute } from "next";
import { absoluteUrl } from "../lib/site-url";
export default function robots(): MetadataRoute.Robots { return {rules:{userAgent:"*",allow:["/en","/ta"],disallow:["/api/","/en/account","/ta/account","/en/admin","/ta/admin"]},sitemap:absoluteUrl("/sitemap.xml")}; }
