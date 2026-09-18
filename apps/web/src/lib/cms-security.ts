export function cmsPath(path: string[], method: string): string | null {
  const id = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";
  const value = path.join("/");
  const base = `organizations/${id}/pages`;
  const rules: Record<string, string[]> = {
    GET: [base, `${base}/${id}`, `${base}/${id}/translations/(en|ta)/(preview|revisions)`],
    POST: [base, `${base}/${id}/translations`, `${base}/${id}/translations/(en|ta)/(publish|archive|restore)`],
    PATCH: [`${base}/${id}/translations/(en|ta)`],
  };
  return rules[method]?.some(rule => new RegExp(`^${rule}$`).test(value)) ? "/cms/" + value : null;
}
