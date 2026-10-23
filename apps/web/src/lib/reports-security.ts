export const reportUuid = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}";

export function reportsPath(path: string[], method: string): string | null {
  const base = `organizations/${reportUuid}`;
  const rules: Record<string, string[]> = {
    GET: [`${base}/(options|dashboard|definitions|snapshots|exports)`, `${base}/(snapshots|exports)/${reportUuid}`,
      `${base}/exports/${reportUuid}/download/[A-Za-z0-9_-]{43}`],
    POST: [`${base}/(snapshots|exports)`, `${base}/exports/${reportUuid}/access`],
  };
  return rules[method]?.some((rule) => new RegExp(`^${rule}$`).test(path.join("/"))) ? `/reports/${path.join("/")}` : null;
}

export function reportQuery(input: URLSearchParams): string | null {
  const output = new URLSearchParams();
  for (const [key, value] of input) {
    if (output.has(key)) return null;
    if (["program_id", "cohort_id", "cursor", "program_cursor", "cohort_cursor"].includes(key)) {
      if (!new RegExp(`^${reportUuid}$`).test(value)) return null;
    } else if (["from_date", "through_date"].includes(key)) {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || Number.isNaN(Date.parse(`${value}T00:00:00Z`)) || new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) !== value) return null;
    } else if (key === "limit") { if (!/^[1-9][0-9]?$|^100$/.test(value)) return null; }
    else return null;
    output.set(key, value);
  }
  return output.toString();
}
