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


export function notificationQuery(path: string, method: string, params: URLSearchParams): string | null {
  const preference = path.endsWith("/preference");
  const mine = path.endsWith("/mine") && method === "GET";
  if ([...params.keys()].some((key) => key !== "topic" && key !== "cursor")) return null;
  if (params.getAll("topic").length > 1 || params.getAll("cursor").length > 1) return null;
  const topic = params.get("topic");
  const cursor = params.get("cursor");
  if (topic === "" || cursor === "") return null;
  if (topic && (!preference || (topic !== "lead_assignment" && topic !== "followup_due"))) return null;
  if (cursor && (!mine || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(cursor))) return null;
  const query = new URLSearchParams();
  if (topic) query.set("topic", topic);
  if (cursor) query.set("cursor", cursor);
  if (mine) query.set("limit", "25");
  return query.toString();
}
