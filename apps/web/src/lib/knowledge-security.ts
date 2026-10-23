const id = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}";

export function knowledgePath(path: string[], method: string): string | null {
  const value = path.join("/");
  const base = `organizations/${id}`;
  const rules: Record<string, string[]> = {
    GET: [`${base}/(items|catalog|mine|funding-cases)`, `${base}/(items|catalog)/${id}`, `${base}/items/${id}/history`],
    POST: [`${base}/items`, `${base}/items/${id}/(publish|draft|archive)`, `${base}/(saved|interests)/${id}`, `${base}/funding-cases`, `${base}/funding-cases/${id}/status`],
    PATCH: [`${base}/items/${id}`],
    DELETE: [`${base}/saved/${id}`],
  };
  return rules[method]?.some((rule) => new RegExp(`^${rule}$`).test(value)) ? `/knowledge/${value}` : null;
}

export function knowledgeQuery(input: URLSearchParams): string | null {
  const output = new URLSearchParams();
  const choices: Record<string, readonly string[]> = {
    locale: ["en", "ta"], kind: ["scheme", "funding", "opportunity"],
    availability: ["active", "open", "upcoming", "closed", "all"],
    state: ["draft", "published", "archived"],
    status: ["interested", "eligibility_check", "document_preparation", "applied", "under_review", "approved", "rejected", "disbursed"],
  };
  for (const [key, value] of input) {
    if (output.has(key)) return null;
    if (choices[key]) { if (!choices[key].includes(value)) return null; }
    else if (["q", "sector", "geography", "tag"].includes(key)) {
      if (!value.trim() || value.length > (key === "tag" ? 200 : 120) || /[\u0000-\u001f\u007f]/.test(value)) return null;
    } else if (["cursor", "saved_cursor", "interest_cursor", "case_cursor"].includes(key)) { if (!new RegExp(`^${id}$`).test(value)) return null; }
    else if (key === "limit") { if (!/^[1-9][0-9]?$|^100$/.test(value)) return null; }
    else return null;
    output.set(key, value);
  }
  return output.toString();
}
