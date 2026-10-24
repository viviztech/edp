const id = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}";

export function selectionAdminPath(path: string[], method: string): string | null {
  const value = path.join("/");
  const rules: Record<string, string[]> = {
    GET: [`organizations/${id}/workspace`, `organizations/${id}/assignments/${id}/documents`, `organizations/${id}/assignments/${id}/documents/${id}/content`],
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

export function selectionQuery(path: string[], method: string, query: URLSearchParams): string | null {
  if (method !== "GET" || path.length !== 5 || path[2] !== "assignments" || path[4] !== "documents") return query.size ? null : "";
  if ([...query.keys()].some(key => query.getAll(key).length !== 1 || !["limit", "cursor"].includes(key))) return null;
  const limit = query.get("limit"), cursor = query.get("cursor");
  if (limit !== null && (!/^[1-9][0-9]{0,2}$/.test(limit) || Number(limit) > 100)) return null;
  if (cursor !== null && !new RegExp(`^${id}$`).test(cursor)) return null;
  return query.size ? `?${query.toString()}` : "";
}
