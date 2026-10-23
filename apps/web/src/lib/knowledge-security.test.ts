import { describe, expect, it } from "vitest";
import { knowledgePath, knowledgeQuery } from "./knowledge-security";
const org = "11111111-1111-4111-8111-111111111111";
const item = "22222222-2222-4222-8222-222222222222";
describe("knowledge BFF allowlist", () => {
  it("allows only staff/participant resource, saved and funding routes with their expected verbs", () => {
    for (const suffix of ["items", `items/${item}`, `items/${item}/history`, "catalog", `catalog/${item}`, "mine", "funding-cases"]) {
      expect(knowledgePath(["organizations", org, ...suffix.split("/")], "GET")).toBe(`/knowledge/organizations/${org}/${suffix}`);
    }
    for (const suffix of ["items", `items/${item}/publish`, `items/${item}/draft`, `items/${item}/archive`, `saved/${item}`, `interests/${item}`, "funding-cases", `funding-cases/${item}/status`]) {
      expect(knowledgePath(["organizations", org, ...suffix.split("/")], "POST")).toBeTruthy();
    }
    expect(knowledgePath(["organizations", org, "items", item], "PATCH")).toBeTruthy();
    expect(knowledgePath(["organizations", org, "saved", item], "DELETE")).toBeTruthy();
    for (const path of [["organizations", org, "..", "auth"], ["organizations", org, "items", item, "delete"], ["public", org, "catalog"], ["organizations", "not-an-id", "mine"]]) expect(knowledgePath(path, "GET")).toBeNull();
    expect(knowledgePath(["organizations", org, "items", item], "DELETE")).toBeNull();
    expect(knowledgePath(["organizations", org, "catalog"], "POST")).toBeNull();
  });
  it("preserves only bounded known query values and rejects duplicates or malformed cursors", () => {
    const query = new URLSearchParams({ locale: "ta", kind: "scheme", availability: "all", q: "equipment", sector: "services", geography: "Tamil Nadu", tag: "enterprise", saved_cursor: item, interest_cursor: item, case_cursor: item, status: "applied", limit: "100" });
    expect(knowledgeQuery(query)).toBe(query.toString());
    for (const query of ["locale=fr", "locale=en&locale=ta", "limit=101", "limit=0", "limit=01", "q=", "q=" + "x".repeat(121), "cursor=..%2Fauth", "sort=private", "availability=draft", "status=cancelled", "q=%00"]) expect(knowledgeQuery(new URLSearchParams(query))).toBeNull();
  });
});
