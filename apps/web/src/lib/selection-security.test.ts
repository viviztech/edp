import { describe, expect, it } from "vitest";
import { selectionAdminPath } from "./selection-security";

const org = "123e4567-e89b-42d3-a456-426614174000";
const item = "123e4567-e89b-42d3-a456-426614174001";

describe("selection BFF allowlist", () => {
  it("allows only the A02.2 workspace commands", () => {
    expect(selectionAdminPath(["organizations", org, "workspace"], "GET")).toContain("/selection/");
    expect(selectionAdminPath(["organizations", org, "cycles"], "POST")).toContain("/selection/");
    expect(selectionAdminPath(["organizations", org, "rubrics", item], "PUT")).toContain("/selection/");
    expect(selectionAdminPath(["organizations", org, "rubrics", item, "publish"], "POST")).toContain("/selection/");
    expect(selectionAdminPath(["organizations", org, "assignments", item, "conflict"], "POST")).toContain("/selection/");
    expect(selectionAdminPath(["organizations", org, "assignments", item, "review"], "PUT")).toContain("/selection/");
    expect(selectionAdminPath(["organizations", org, "assignments", item, "submit"], "POST")).toContain("/selection/");
    expect(selectionAdminPath(["organizations", org, "assignments", item, "moderation"], "POST")).toContain("/selection/");    expect(selectionAdminPath(["organizations", org, "interviews"], "POST")).toContain("/selection/");
    expect(selectionAdminPath(["organizations", org, "interviews", item, "score"], "POST")).toContain("/selection/");
    expect(selectionAdminPath(["organizations", org, "interviews", item, "complete"], "POST")).toContain("/selection/");
    expect(selectionAdminPath(["organizations", org, "cycles", item, "applications", item, "decision"], "POST")).toContain("/selection/");
  });

  it("rejects traversal, deletes and future decision routes", () => {
    expect(selectionAdminPath(["organizations", org, "..", "auth"], "GET")).toBeNull();
    expect(selectionAdminPath(["organizations", org, "cycles", item], "DELETE")).toBeNull();
    expect(selectionAdminPath(["organizations", org, "decisions"], "POST")).toBeNull();
  });
});