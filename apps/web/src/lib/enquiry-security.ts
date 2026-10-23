const uuid = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";
export const isEnquiryId = (value: string) => new RegExp(`^${uuid}$`).test(value);

export function enquiryPath(parts: string[], method: string): string | null {
  const base = `organizations/${uuid}/enquiries`;
  const rules: Record<string, string[]> = {
    GET: [`${base}/queue`, `${base}/${uuid}`],
    POST: [`${base}/${uuid}/status`],
  };
  const value = parts.join("/");
  return rules[method]?.some(rule => new RegExp(`^${rule}$`).test(value)) ? `/cms/${value}` : null;
}

export function enquiryQuery(input: URLSearchParams, path: string, method: string): string | null {
  const output = new URLSearchParams();
  const collection = method === "GET" && /\/enquiries\/queue$/.test(path);
  for (const [key, value] of input) {
    if (!collection || output.has(key)) return null;
    if (key === "limit") { if (!/^[1-9][0-9]?$|^100$/.test(value)) return null; }
    else if (key === "cursor") { if (!isEnquiryId(value)) return null; }
    else if (key === "status") { if (!["new", "reviewed", "closed"].includes(value)) return null; }
    else return null;
    output.set(key, value);
  }
  return output.toString();
}

// A configured privacy notice must be a local document or a secure absolute URL.
export function safePrivacyUrl(value: string): boolean {
  if (/^\/(en|ta)\/pages\/[a-z0-9]+(?:-[a-z0-9]+)*$/.test(value)) return true;
  try { const url = new URL(value); return url.protocol === "https:" && !url.username && !url.password && value.length <= 2048; }
  catch { return false; }
}
