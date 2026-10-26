const uuid = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}";
const base = `organizations/${uuid}/profiles/${uuid}`;

export function businessToolsPath(path: string[], method: string): string | null {
  const value = path.join("/");
  const rules: Record<string, string[]> = {
    GET: [`${base}/card`, `${base}/card/artifact`, `${base}/catalogue`, `${base}/catalogue/items/${uuid}`, `${base}/contacts/${uuid}`, `${base}/tasks/${uuid}`, `${base}/quotes`,
      `${base}/quotes/${uuid}`, `${base}/quotes/${uuid}/artifact`, `${base}/contacts`, `${base}/tasks`, `${base}/history`],
    POST: [`${base}/card`, `${base}/card/sharing`, `${base}/catalogue/sharing`, `${base}/catalogue/items`,
      `${base}/catalogue/items/${uuid}/update`, `${base}/quotes`, `${base}/quotes/${uuid}/update`, `${base}/quotes/${uuid}/issue`,
      `${base}/contacts`, `${base}/contacts/${uuid}/update`, `${base}/tasks`, `${base}/tasks/${uuid}/update`],
  };
  return rules[method]?.some(rule => new RegExp(`^${rule}$`).test(value)) ? `/business-tools/${value}` : null;
}

export function businessToolsQuery(path: string[], method: string, query: URLSearchParams): string | null {
  if (!query.size) return "";
  const leaf = path.at(-1);
  if (method !== "GET" || !["catalogue", "quotes", "contacts", "tasks", "history"].includes(leaf ?? "")) return null;
  for (const [key, value] of query) {
    if (query.getAll(key).length !== 1) return null;
    if (key === "limit" && /^(?:[1-9]|[1-4][0-9]|50)$/.test(value)) continue;
    if (key === "offset" && /^(?:0|[1-9][0-9]{0,3}|10000)$/.test(value)) continue;
    if (leaf === "tasks" && key === "contact_id" && new RegExp(`^${uuid}$`).test(value)) continue;
    if (leaf === "tasks" && key === "status" && ["pending", "completed", "cancelled"].includes(value)) continue;
    if (leaf === "contacts" && key === "status" && ["lead", "customer", "archived"].includes(value)) continue;
    if (leaf === "contacts" && key === "search" && value.length <= 160 && !/[\u0000-\u001f\u007f]/.test(value)) continue;
    if (leaf === "history" && key === "kind" && ["card", "catalogue", "catalogue_item", "quote", "contact", "task"].includes(value)) continue;
    if (leaf === "history" && key === "resource_id" && new RegExp(`^${uuid}$`).test(value)) continue;
    return null;
  }
  return `?${query.toString()}`;
}
