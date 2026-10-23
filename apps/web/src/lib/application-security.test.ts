import { describe, expect, it } from "vitest";
import { applicationPath, applicationQuery } from "./application-security";

const id = "11111111-1111-4111-8111-111111111111";

describe("applicationPath", () => {
  it("allows bounded applicant cycle, draft and submission routes", () => {
    expect(applicationPath(["mine"], "GET")).toBe("/applications/mine");
    expect(applicationPath(["organizations", id, "cycles"], "GET")).toContain("/applications/");
    expect(applicationPath(["organizations", id, "cycles", id, "application"], "GET")).toContain("/applications/");
    expect(applicationPath(["organizations", id, "cycles", id, "draft"], "POST")).toContain("/applications/");
    expect(applicationPath(["organizations", id, "draft", id], "PATCH")).toContain("/applications/");
    expect(applicationPath(["organizations", id, "draft", id, "submit"], "POST")).toContain("/applications/");
  });
  it("allows only bounded self-history pagination and rejects scope overrides", () => {
    expect(applicationQuery(["mine"], "GET", new URLSearchParams(`limit=20&cursor=${id}`))).toBe(`?limit=20&cursor=${id}`);
    for (const query of ["owner=other", "organization=other", "limit=0", "limit=101", "limit=1&limit=2", "cursor=invalid", `cursor=${id}&cursor=${id}`, "limit=1e2"]) {
      expect(applicationQuery(["mine"], "GET", new URLSearchParams(query))).toBeNull();
    }
    expect(applicationPath(["mine"], "POST")).toBeNull();
    expect(applicationQuery(["organizations", id, "cycles"], "GET", new URLSearchParams("limit=20"))).toBeNull();
  });
  it("rejects staff, malformed and unscoped submission routes", () => {
    expect(applicationPath(["organizations", id, "submit"], "POST")).toBeNull();
    expect(applicationPath(["organizations", id, "all"], "GET")).toBeNull();
    expect(applicationPath(["organizations", "invalid", "cycles"], "GET")).toBeNull();
    expect(applicationPath(["organizations", id, "cycles", id, "application"], "POST")).toBeNull();
  });
});
