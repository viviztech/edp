import { describe, expect, it } from "vitest";
import { metaPath } from "./meta-security";

const id = "11111111-1111-4111-8111-111111111111";

describe("metaPath", () => {
  it("allows only explicit operational routes", () => {
    expect(metaPath(["organizations", id, "health"], "GET")).toContain("/meta/");
    expect(metaPath(["organizations", id, "integrations", id, "rotate"], "POST")).toContain("/meta/");
    expect(metaPath(["organizations", id, "integrations", id, "mappings", id], "PATCH")).toContain("/meta/");
    expect(metaPath(["organizations", id, "events", id, "replay"], "POST")).toContain("/meta/");
  });
  it("rejects provider and arbitrary upstream routes", () => {
    expect(metaPath(["integrations", "meta", "webhook", id], "POST")).toBeNull();
    expect(metaPath(["organizations", id, "events", id, "replay"], "GET")).toBeNull();
    expect(metaPath(["organizations", id, "integrations"], "DELETE")).toBeNull();
  });
});
