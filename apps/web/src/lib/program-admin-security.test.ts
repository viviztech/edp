import { describe, expect, it } from "vitest";
import { programAdminPath } from "./program-admin-security";

const org = "123e4567-e89b-42d3-a456-426614174000";
const item = "123e4567-e89b-42d3-a456-426614174001";

describe("program administration BFF allowlist", () => {
  it("allows catalog, create, update and explicit state commands", () => {
    expect(programAdminPath(["organizations", org, "catalog"], "GET")).toBe(`/programs/organizations/${org}/catalog`);

  expect(programAdminPath(["organizations", org, "my-timeline"], "GET")).toBe(`/programs/organizations/${org}/my-timeline`);
  expect(programAdminPath(["organizations", org, "enrollments", "convert"], "POST")).toBe(`/programs/organizations/${org}/enrollments/convert`);
  expect(programAdminPath(["organizations", org, "sessions"], "POST")).toBe(`/programs/organizations/${org}/sessions`);
  expect(programAdminPath(["organizations", org, "sessions", org, "state"], "POST")).toBe(`/programs/organizations/${org}/sessions/${org}/state`);
  expect(programAdminPath(["organizations", org, "participants", org, "state"], "POST")).toBe(`/programs/organizations/${org}/participants/${org}/state`);
  expect(programAdminPath(["organizations", org, "staff-assignments"], "POST")).toBe(`/programs/organizations/${org}/staff-assignments`);
  expect(programAdminPath(["organizations", org, "staff-assignments", item, "revoke"], "POST")).toBe(`/programs/organizations/${org}/staff-assignments/${item}/revoke`);
    expect(programAdminPath(["organizations", org, "programs"], "POST")).toContain("/programs/");
    expect(programAdminPath(["organizations", org, "cohorts", item], "PATCH")).toContain("/programs/");
    expect(programAdminPath(["organizations", org, "cycles", item, "state"], "POST")).toContain("/programs/");
  });

  it("rejects traversal, deletes and unknown resources", () => {
    expect(programAdminPath(["organizations", org, "..", "auth"], "GET")).toBeNull();
    expect(programAdminPath(["organizations", org, "programs", item], "DELETE")).toBeNull();
    expect(programAdminPath(["organizations", org, "participants"], "POST")).toBeNull();
    expect(programAdminPath(["organizations", org, "staff-assignments", item], "DELETE")).toBeNull();
  });
});
