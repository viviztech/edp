const id = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}";

export function businessPlanPath(path: string[], method: string): string | null {
  const value = path.join("/");
  const rules: Record<string, string[]> = {
    GET: [`organizations/${id}/mine`, `organizations/${id}/assigned`],
    POST: [
      `organizations/${id}/enrollments/${id}`,
      `organizations/${id}/enrollments/${id}/sections`,
      `organizations/${id}/enrollments/${id}/submit`,
      `organizations/${id}/submissions/${id}/review`,
    ],
  };
  return rules[method]?.some((rule) => new RegExp(`^${rule}$`).test(value))
    ? `/business-plans/${value}` : null;
}
