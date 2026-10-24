const id = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}";
const token = "[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+";

export function learningPath(path: string[], method: string): string | null {
  const value = path.join("/");
  const rules: Record<string, string[]> = {
    GET: [
      `organizations/${id}/catalog`,
      `organizations/${id}/my-learning`,
      `organizations/${id}/trainer-delivery`,
      `organizations/${id}/material-delivery/${token}`,
      `organizations/${id}/my-learning/${id}/assignments/${id}/files(?:/${id}(?:/content)?)?`,
      `organizations/${id}/trainer-delivery/${id}/assignment-submissions/${id}/files(?:/${id}/content)?`,
      `organizations/${id}/courses/${id}/assignments/${id}/file-rule`,
      `organizations/${id}/courses/${id}/material-files(?:/${id}(?:/content)?)?`,
    ],
    POST: [
      `organizations/${id}`,
      `organizations/${id}/(modules|lessons|materials|prerequisites|cohort-assignments|assignments|quizzes|quiz-questions|quiz-choices|certificate-templates)`,
      `organizations/${id}/${id}/(publish|completion-rule)`,
      `organizations/${id}/certificate-templates/${id}/publish`,
      `organizations/${id}/certificates/issue`,
      `organizations/${id}/certificates/${id}/revoke`,
      `organizations/${id}/my-learning/${id}/start`,
      `organizations/${id}/my-learning/${id}/lessons/${id}/complete`,
      `organizations/${id}/my-learning/${id}/quizzes/${id}/attempts`,
      `organizations/${id}/my-learning/${id}/assignments/${id}/submissions`,
      `organizations/${id}/trainer-delivery/${id}/assignment-submissions/${id}/grade`,
      `organizations/${id}/my-learning/${id}/materials/${id}/access`,
      `organizations/${id}/trainer-delivery/${id}/materials/${id}/access`,
      `organizations/${id}/my-learning/${id}/assignments/${id}/files`,
      `organizations/${id}/material-files`,
    ],
    PUT: [
      `organizations/${id}/my-learning/${id}/assignments/${id}/files/${id}/content`,
      `organizations/${id}/courses/${id}/material-files/${id}/content`,
      `organizations/${id}/courses/${id}/assignments/${id}/file-rule`,
    ],
    DELETE: [
      `organizations/${id}/my-learning/${id}/assignments/${id}/files/${id}`,
      `organizations/${id}/courses/${id}/material-files/${id}`,
    ],
  };
  return rules[method]?.some((rule) => new RegExp(`^${rule}$`).test(value))
    ? `/courses/${value}`
    : null;
}

export function learningQuery(path: string, query: URLSearchParams): boolean {
  const paged = /\/courses\/[^/]+\/material-files$/.test(path);
  return [...query.keys()].every((key) => paged && ["cursor", "limit"].includes(key) && query.getAll(key).length === 1)
    && (!query.has("cursor") || new RegExp(`^${id}$`).test(query.get("cursor") ?? ""))
    && (!query.has("limit") || /^(?:[1-9][0-9]?|100)$/.test(query.get("limit") ?? ""));
}
