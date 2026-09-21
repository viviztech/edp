export function metaPath(path: string[], method: string): string | null {
  const uuid = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";
  const root = `organizations/${uuid}`;
  const integrations = `${root}/integrations`;
  const events = `${root}/events`;
  const rules: Record<string, string[]> = {
    GET: [integrations, `${integrations}/${uuid}/mappings`, events, `${root}/health`],
    POST: [integrations, `${integrations}/${uuid}/mappings`, `${integrations}/${uuid}/rotate`, `${events}/${uuid}/replay`],
    PATCH: [`${integrations}/${uuid}`, `${integrations}/${uuid}/mappings/${uuid}`],
  };
  const value = path.join("/");
  return rules[method]?.some((rule) => new RegExp(`^${rule}$`).test(value))
    ? `/meta/${value}`
    : null;
}
