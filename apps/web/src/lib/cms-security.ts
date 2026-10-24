const id = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";

export function cmsPath(path: string[], method: string): string | null {
  const value = path.join("/");
  const base = `organizations/${id}/pages`;
  const editorial = `organizations/${id}/editorial`;
  const assets = `organizations/${id}/assets`;
  const rules: Record<string, string[]> = {
    GET: [base, `${base}/${id}`, `${base}/${id}/translations/(en|ta)/(preview|revisions)`, editorial, `${editorial}/${id}`, assets, `${assets}/policy`, `${assets}/${id}`, `${assets}/${id}/source/content`],
    POST: [base, `${base}/${id}/translations`, `${base}/${id}/translations/(en|ta)/(publish|archive|restore)`, editorial, `${editorial}/${id}/(publish|archive|restore)`, assets, `${assets}/${id}/(source|prepare|publish|revoke)`],
    PATCH: [`${base}/${id}/translations/(en|ta)`, `${editorial}/${id}`],
    PUT: [`${assets}/${id}/source/content`],
  };
  return rules[method]?.some(rule => new RegExp(`^${rule}$`).test(value)) ? "/cms/" + value : null;
}

export function cmsSourceContent(path: string[]): boolean {
  return path.length === 6 && path[2] === "assets" && path[4] === "source" && path[5] === "content";
}

export function cmsQuery(path: string[], method: string, input: URLSearchParams): string | null {
  const collection = path.length === 3 && ["pages", "editorial", "assets"].includes(path[2]);
  const history = path[2] === "pages" && path.length === 7 && path[6] === "revisions";
  const paginated = method === "GET" && (collection || history);
  const output = new URLSearchParams();
  for (const [key, value] of input) {
    if (output.has(key) || !paginated) return null;
    if (key === "limit") { if (!/^(?:[1-9][0-9]?|100)$/.test(value)) return null; }
    else if (key === "cursor") { if (!new RegExp(`^${id}$`).test(value)) return null; }
    else if (key === "kind" && path[2] === "editorial") { if (!["news", "event", "faq", "testimonial"].includes(value)) return null; }
    else if (key === "locale" && path[2] === "editorial") { if (!["en", "ta"].includes(value)) return null; }
    else if (key === "slug" && path[2] === "editorial") { if (value.length > 120 || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(value)) return null; }
    else return null;
    output.set(key, value);
  }
  if (paginated && !output.has("limit")) output.set("limit", "25");
  return output.toString();
}
