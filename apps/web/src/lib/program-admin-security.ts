const id = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}";

export function programAdminPath(path: string[], method: string): string | null {
  const value = path.join("/");
  const rules: Record<string, string[]> = {
    GET: [`organizations/${id}/catalog`],
    POST: [
      `organizations/${id}/(programs|centers|cohorts|cycles)`,
      `organizations/${id}/(programs|centers|cohorts|cycles)/${id}/state`,
    ],
    PATCH: [`organizations/${id}/(programs|centers|cohorts|cycles)/${id}`],
  };
  return rules[method]?.some((rule) => new RegExp(`^${rule}$`).test(value))
    ? `/programs/${value}`
    : null;
}
