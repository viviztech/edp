const id = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}";

export function learningPath(path: string[], method: string): string | null {
  const value = path.join("/");
  const rules: Record<string, string[]> = {
    GET: [
      `organizations/${id}/catalog`,
      `organizations/${id}/my-learning`,
    ],
    POST: [
      `organizations/${id}`,
      `organizations/${id}/(modules|lessons|materials|cohort-assignments)`,
      `organizations/${id}/${id}/publish`,
      `organizations/${id}/my-learning/${id}/start`,
    ],
  };
  return rules[method]?.some((rule) => new RegExp(`^${rule}$`).test(value))
    ? `/courses/${value}`
    : null;
}
