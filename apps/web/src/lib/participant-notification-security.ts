const uuid = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";
export function participantNotificationPath(parts: string[], method: string): string | null {
  const value = parts.join("/"), root = `organizations/${uuid}`;
  const patterns = method === "GET" ? [`${root}/mine`, `${root}/preference`]
    : method === "POST" ? [`${root}/preference`, `${root}/${uuid}/read`] : [];
  return patterns.some(pattern => new RegExp(`^${pattern}$`).test(value)) ? `/participant-notifications/${value}` : null;
}
export function participantNotificationQuery(path: string, method: string, params: URLSearchParams): string | null {
  const list = method === "GET" && path.endsWith("/mine"), allowed = list ? ["cursor", "limit"] : [];
  for (const key of params.keys()) if (!allowed.includes(key) || params.getAll(key).length !== 1) return null;
  if (!list) return "";
  const query = new URLSearchParams(), cursor = params.get("cursor"), limit = params.get("limit") ?? "25";
  if (!/^(?:[1-9][0-9]?|100)$/.test(limit)) return null;
  if (cursor !== null) {
    if (!new RegExp(`^${uuid}$`).test(cursor)) return null;
    query.set("cursor", cursor);
  }
  query.set("limit", limit);
  return query.toString();
}
