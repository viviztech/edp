const id = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}";

export function attendancePath(path: string[], method: string): string | null {
  const value = path.join("/");
  const rules: Record<string, string[]> = {
    GET: [
      `organizations/${id}/staff-workspace`,
      `organizations/${id}/my-attendance`,
    ],
    POST: [
      `organizations/${id}/windows`,
      `organizations/${id}/windows/${id}/close`,
      `organizations/${id}/sessions/${id}/records`,
      `organizations/${id}/records/${id}/correct`,
      `organizations/${id}/check-in`,
    ],
    PUT: [`organizations/${id}/policy`],
  };
  return rules[method]?.some((rule) => new RegExp(`^${rule}$`).test(value))
    ? `/attendance/${value}`
    : null;
}
