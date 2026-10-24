export function crmPath(path: string[], method: string): string | null {
  const uuid = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";
  const value = path.join("/");
  const root = `organizations/${uuid}`;
  const leads = `${root}/leads`;
  const reviews = `${root}/duplicate-reviews`;
  const exports = `${root}/exports`;
  const tags = `${root}/tags`;
  const rules: Record<string, string[]> = {
    GET: [leads, tags, `${leads}/${uuid}/tags`, `${leads}/${uuid}/activities`, `${leads}/${uuid}/registration-link`, reviews, exports, `${exports}/${uuid}`, `${exports}/${uuid}/download`],
    POST: [leads, tags, `${leads}/${uuid}/activities`, `${leads}/${uuid}/activities/${uuid}/complete`, `${leads}/${uuid}/tags/${uuid}/attach`, `${leads}/${uuid}/tags/${uuid}/detach`, `${leads}/${uuid}/registration-link`, reviews, `${reviews}/${uuid}/resolve`, exports],
    PATCH: [`${leads}/${uuid}`],
  };
  return rules[method]?.some((rule) => new RegExp(`^${rule}$`).test(value)) ? `/crm/${value}` : null;
}

export function crmExportQuery(input: URLSearchParams, collection: boolean): URLSearchParams | null {
  const query = new URLSearchParams();
  const allowed = collection ? ["cursor", "limit"] : [];
  for (const key of input.keys()) {
    if (!allowed.includes(key) || input.getAll(key).length !== 1) return null;
  }
  if (!collection) return query;
  const cursor = input.get("cursor"), limit = input.get("limit") ?? "25";
  if (!/^(?:[1-9][0-9]?|100)$/.test(limit)) return null;
  if (cursor !== null) {
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(cursor)) return null;
    query.set("cursor", cursor);
  }
  query.set("limit", limit);
  return query;
}
