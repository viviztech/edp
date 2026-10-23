const id = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";
const purposes = ["application_document", "cms_asset", "assignment_submission", "lms_material", "helpdesk_attachment"];
export function filePolicyPath(parts: string[], method: string): string | null {
  const base = `organizations/${id}/policies`;
  const rules: Record<string, string[]> = {
    GET: [base, `${base}/${id}`], POST: [base, `${base}/${id}/(publish|retire)`], PATCH: [`${base}/${id}`],
  };
  const value = parts.join("/");
  return rules[method]?.some(rule => new RegExp(`^${rule}$`).test(value)) ? `/files/${value}` : null;
}
export function filePolicyQuery(parts: string[], method: string, input: URLSearchParams): string | null {
  const collection = method === "GET" && parts.length === 3;
  const output = new URLSearchParams();
  for (const [key, value] of input) {
    if (!collection || output.has(key)) return null;
    if (key === "purpose") { if (!purposes.includes(value)) return null; }
    else if (key === "cursor") { if (!new RegExp(`^${id}$`).test(value)) return null; }
    else if (key === "limit") { if (!/^(?:[1-9][0-9]?|100)$/.test(value)) return null; }
    else return null;
    output.set(key, value);
  }
  if (collection && !output.has("limit")) output.set("limit", "25");
  return output.toString();
}
