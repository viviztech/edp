const uuid = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}";

export function helpdeskPath(parts: string[], method: string): string | null {
  const base = `organizations/${uuid}`;
  const rules: Record<string, string[]> = {
    GET: [`${base}/(tickets|assignees|notices|preference)`, `${base}/tickets/${uuid}`, `${base}/tickets/${uuid}/(messages|history)`, `${base}/tickets/${uuid}/attachments/${uuid}`],
    POST: [`${base}/tickets`, `${base}/tickets/${uuid}/(messages|assignment|priority|status|reopen)`, `${base}/notices/${uuid}/read`, `${base}/preference`],
  };
  const path = parts.join("/");
  return rules[method]?.some((rule) => new RegExp(`^${rule}$`).test(path)) ? `/helpdesk/${path}` : null;
}

export function helpdeskQuery(input: URLSearchParams): string | null {
  const output = new URLSearchParams();
  const values: Record<string, readonly string[]> = {
    status: ["open", "assigned", "in_progress", "waiting_for_user", "resolved", "closed"],
    category: ["funding", "registration", "tax_compliance", "marketing", "technology", "business_planning", "banking", "mentoring", "general"],
    priority: ["low", "normal", "high", "urgent"], queue: ["mine", "assigned", "unassigned", "organization"],
  };
  for (const [key, value] of input) {
    if (output.has(key)) return null;
    if (values[key]) { if (!values[key].includes(value)) return null; }
    else if (key === "cursor") { if (!new RegExp(`^${uuid}$`).test(value)) return null; }
    else if (key === "limit") { if (!/^[1-9][0-9]?$|^100$/.test(value)) return null; }
    else return null;
    output.set(key, value);
  }
  return output.toString();
}
