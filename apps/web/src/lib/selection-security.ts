const id = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}";

export function selectionAdminPath(path: string[], method: string): string | null {
  const value = path.join("/");
  const rules: Record<string, string[]> = {
    GET: [`organizations/${id}/workspace`],
    POST: [
      `organizations/${id}/cycles`,
      `organizations/${id}/cycles/${id}/state`,
      `organizations/${id}/rubrics/${id}/(publish|copy)`,
      `organizations/${id}/assignments`,
      `organizations/${id}/assignments/${id}/conflict`,
      `organizations/${id}/assignments/${id}/(submit|moderation)`,
      `organizations/${id}/interviews`,
      `organizations/${id}/interviews/${id}/(score|complete)`,
      `organizations/${id}/cycles/${id}/applications/${id}/decision`,
    ],
    PATCH: [`organizations/${id}/cycles/${id}`],
    PUT: [`organizations/${id}/rubrics/${id}`,
      `organizations/${id}/assignments/${id}/review`,
    ],
  };
  return rules[method]?.some((rule) => new RegExp(`^${rule}$`).test(value))
    ? `/selection/${value}`
    : null;
}