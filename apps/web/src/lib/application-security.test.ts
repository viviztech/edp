import { describe, expect, it } from "vitest";
import { applicationPath } from "./application-security";

const id = "11111111-1111-4111-8111-111111111111";

describe("applicationPath", () => {
  it("allows bounded applicant cycle, draft and submission routes", () => {
    expect(applicationPath(["organizations", id, "cycles"], "GET")).toContain("/applications/");
    expect(applicationPath(["organizations", id, "cycles", id, "application"], "GET")).toContain("/applications/");
    expect(applicationPath(["organizations", id, "cycles", id, "draft"], "POST")).toContain("/applications/");
    expect(applicationPath(["organizations", id, "draft", id], "PATCH")).toContain("/applications/");
    expect(applicationPath(["organizations", id, "draft", id, "submit"], "POST")).toContain("/applications/");
  });
  it("rejects staff, malformed and unscoped submission routes", () => {
    expect(applicationPath(["organizations", id, "submit"], "POST")).toBeNull();
    expect(applicationPath(["organizations", id, "all"], "GET")).toBeNull();
    expect(applicationPath(["organizations", "invalid", "cycles"], "GET")).toBeNull();
    expect(applicationPath(["organizations", id, "cycles", id, "application"], "POST")).toBeNull();
  });
});