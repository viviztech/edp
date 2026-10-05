const id = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}";

export function mentoringPath(path: string[], method: string): string | null {
  const value = path.join("/");
  const rules: Record<string, string[]> = {
    GET: [`organizations/${id}/workspace`, `organizations/${id}/my-mentoring`],
    POST: [
      `organizations/${id}/profiles`, `organizations/${id}/expertise`,
      `organizations/${id}/availability`, `organizations/${id}/assignments`,
      `organizations/${id}/assignments/${id}/end`, `organizations/${id}/sessions`,
      `organizations/${id}/sessions/${id}/state`, `organizations/${id}/notes`,
      `organizations/${id}/goals`, `organizations/${id}/goals/${id}/state`,
      `organizations/${id}/action-items`, `organizations/${id}/action-items/${id}/state`,
      `organizations/${id}/follow-ups`, `organizations/${id}/follow-ups/${id}/state`,
      `organizations/${id}/feedback`,
    ],
  };
  return rules[method]?.some((rule) => new RegExp(`^${rule}$`).test(value))
    ? `/mentoring/${value}` : null;
}
