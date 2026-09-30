const id = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}";
const token = "[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+";

export function learningPath(path: string[], method: string): string | null {
  const value = path.join("/");
  const rules: Record<string, string[]> = {
    GET: [
      `organizations/${id}/catalog`,
      `organizations/${id}/my-learning`,
      `organizations/${id}/trainer-delivery`,
      `organizations/${id}/material-delivery/${token}`,
    ],
    POST: [
      `organizations/${id}`,
      `organizations/${id}/(modules|lessons|materials|prerequisites|cohort-assignments)`,
      `organizations/${id}/${id}/(publish|completion-rule)`,
      `organizations/${id}/my-learning/${id}/start`,
      `organizations/${id}/my-learning/${id}/lessons/${id}/complete`,
      `organizations/${id}/my-learning/${id}/materials/${id}/access`,
      `organizations/${id}/trainer-delivery/${id}/materials/${id}/access`,
    ],
  };
  return rules[method]?.some((rule) => new RegExp(`^${rule}$`).test(value))
    ? `/courses/${value}`
    : null;
}
