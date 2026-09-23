export function applicationPath(path: string[], method: string): string | null {
  const id = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";
  const root = `organizations/${id}`;
  const rules: Record<string, string[]> = {
    GET: [
      `${root}/form`,
      `${root}/draft`,
      `${root}/cycles`,
      `${root}/cycles/${id}/application`,
    ],
    POST: [
      `${root}/draft`,
      `${root}/cycles/${id}/draft`,
      `${root}/draft/${id}/submit`,
    ],
    PATCH: [`${root}/draft/${id}`],
  };
  const value = path.join("/");
  return rules[method]?.some((rule) => new RegExp(`^${rule}$`).test(value))
    ? `/applications/${value}`
    : null;
}