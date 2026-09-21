export function siteUrl(): URL {
  const raw = process.env.PUBLIC_SITE_URL ?? process.env.NEXT_PUBLIC_SITE_URL ?? "http://127.0.0.1:3001";
  try { return new URL(raw.endsWith("/") ? raw : `${raw}/`); } catch { return new URL("http://127.0.0.1:3001/"); }
}
export function absoluteUrl(path: string): string { return new URL(path.replace(/^\//, ""), siteUrl()).toString(); }
