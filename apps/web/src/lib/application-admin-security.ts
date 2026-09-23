export function applicationAdminPath(path: string[], method: string): string | null {
  const uuid = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";
  const definitions = `organizations/${uuid}/definitions`;
  const rules: Record<string, string[]> = {
    GET: [definitions, `${definitions}/${uuid}`],
    POST: [definitions, `${definitions}/${uuid}/copy`, `${definitions}/${uuid}/publish`],
    PATCH: [`${definitions}/${uuid}`],
  };
  const value = path.join("/");
  return rules[method]?.some((rule) => new RegExp(`^${rule}$`).test(value))
    ? `/applications/${value}`
    : null;
}
