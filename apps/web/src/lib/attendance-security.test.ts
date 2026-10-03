import { describe, expect, it } from "vitest";
import { attendancePath } from "./attendance-security";

const org = "123e4567-e89b-42d3-a456-426614174000";
const item = "123e4567-e89b-42d3-a456-426614174001";

describe("attendance BFF allowlist", () => {
  it("allows only the attendance workspace and commands", () => {
    expect(attendancePath(["organizations", org, "staff-workspace"], "GET"))
      .toBe(`/attendance/organizations/${org}/staff-workspace`);
    expect(attendancePath(["organizations", org, "policy"], "PUT"))
      .toBe(`/attendance/organizations/${org}/policy`);
    expect(attendancePath(["organizations", org, "check-in"], "POST"))
      .toBe(`/attendance/organizations/${org}/check-in`);
  });

  it("rejects traversal, deletes, short tokens and unknown commands", () => {
    expect(attendancePath(["organizations", org, "..", "auth"], "GET")).toBeNull();
    expect(attendancePath(["organizations", org, "policy"], "DELETE")).toBeNull();
    expect(attendancePath(["organizations", org, "windows", item, "qr", "a".repeat(43)], "GET"))
      .toBeNull();
    expect(attendancePath(["organizations", org, "records"], "POST")).toBeNull();
  });
});
