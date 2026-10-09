const id = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}";

export function businessPath(path: string[], method: string): string | null {
  const value = path.join("/");
  const rules: Record<string, string[]> = {
    GET: [`organizations/${id}/mine`, `organizations/${id}/staff`],
    POST: [`organizations/${id}/profiles`, `organizations/${id}/profiles/${id}/update`,
      `organizations/${id}/follow-ups/${id}/outcome`, `organizations/${id}/policy`],
  };
  return rules[method]?.some((rule) => new RegExp(`^${rule}$`).test(value))
    ? `/businesses/${value}` : null;
}
