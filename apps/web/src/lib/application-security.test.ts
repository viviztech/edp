import { describe, expect, it } from "vitest";
import { applicationPath } from "./application-security";

const id = "11111111-1111-4111-8111-111111111111";

describe("applicationPath", () => {
  it("allows only bounded applicant draft routes", () => {
    expect(applicationPath(["organizations", id, "form"], "GET")).toContain("/applications/");
    expect(applicationPath(["organizations", id, "draft"], "POST")).toContain("/applications/");
    expect(applicationPath(["organizations", id, "draft", id], "PATCH")).toContain("/applications/");
  });
  it("rejects submission, staff and malformed routes", () => {
    expect(applicationPath(["organizations", id, "submit"], "POST")).toBeNull();
    expect(applicationPath(["organizations", id, "all"], "GET")).toBeNull();
    expect(applicationPath(["organizations", "invalid", "draft"], "GET")).toBeNull();
  });
});
