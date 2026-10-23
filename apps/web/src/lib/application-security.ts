export function applicationPath(path: string[], method: string): string | null {
  const id = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";
  const root = `organizations/${id}`;
  const rules: Record<string, string[]> = {
    GET: [
      "mine",
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

export function applicationQuery(path: string[], method: string, search: URLSearchParams): string | null {
  if ([...search.keys()].some((key) => search.getAll(key).length !== 1)) return null;
  if (path.length !== 1 || path[0] !== "mine" || method !== "GET") return search.size === 0 ? "" : null;
  if ([...search.keys()].some((key) => key !== "limit" && key !== "cursor")) return null;
  const limit = search.get("limit");
  const cursor = search.get("cursor");
  if (limit !== null && (!/^[1-9][0-9]{0,2}$/.test(limit) || Number(limit) > 100)) return null;
  if (cursor !== null && !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(cursor)) return null;
  return search.size ? `?${search.toString()}` : "";
}
