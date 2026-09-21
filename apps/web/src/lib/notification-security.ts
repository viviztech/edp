export function notificationPath(path: string[], method: string): string | null {
  const id = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";
  const root = `organizations/${id}`;
  const rules: Record<string, string[]> = {
    GET: [`${root}/mine`, `${root}/preference`],
    POST: [`${root}/preference`, `${root}/${id}/read`],
  };
  const value = path.join("/");
  return rules[method]?.some((rule) => new RegExp(`^${rule}$`).test(value))
    ? `/notifications/${value}`
    : null;
}
