import { reportUuid } from "./reports-security";

export function impactPath(path: string[], method: string): string | null {
  const base = `organizations/${reportUuid}`;
  const rules: Record<string, string[]> = {
    GET: [`${base}/(definitions|mine)`],
    POST: [`${base}/(definitions|records)`, `${base}/definitions/${reportUuid}/(publish|archive)`],
  };
  return rules[method]?.some((rule) => new RegExp(`^${rule}$`).test(path.join("/"))) ? `/impact/${path.join("/")}` : null;
}

export function impactQuery(input: URLSearchParams): string | null {
  const output = new URLSearchParams();
  for (const [key, value] of input) {
    if (output.has(key)) return null;
    if (["cursor", "definition_cursor", "record_cursor", "enrollment_cursor", "enrollment_id"].includes(key)) {
      if (!new RegExp(`^${reportUuid}$`).test(value)) return null;
    } else if (key === "limit") { if (!/^[1-9][0-9]?$|^100$/.test(value)) return null; }
    else if (key === "state") { if (!["draft", "published", "archived"].includes(value)) return null; }
    else if (key === "stage") { if (!["baseline", "outcome"].includes(value)) return null; }
    else if (key === "observed_on") { if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || Number.isNaN(Date.parse(`${value}T00:00:00Z`)) || new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) !== value) return null; }
    else return null;
    output.set(key, value);
  }
  return output.toString();
}
