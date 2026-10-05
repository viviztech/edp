import { describe, expect, it } from "vitest";
import { mentoringPath } from "./mentoring-security";

const org = "123e4567-e89b-42d3-a456-426614174000";
const item = "123e4567-e89b-42d3-a456-426614174001";

describe("mentoring BFF allowlist", () => {
  it("allows documented reads and commands", () => {
    expect(mentoringPath(["organizations", org, "workspace"], "GET"))
      .toBe(`/mentoring/organizations/${org}/workspace`);
    expect(mentoringPath(["organizations", org, "sessions", item, "state"], "POST"))
      .toBe(`/mentoring/organizations/${org}/sessions/${item}/state`);
    expect(mentoringPath(["organizations", org, "feedback"], "POST"))
      .toBe(`/mentoring/organizations/${org}/feedback`);
  });
  it("rejects traversal, deletes and unknown paths", () => {
    expect(mentoringPath(["organizations", org, "..", "auth"], "GET")).toBeNull();
    expect(mentoringPath(["organizations", org, "sessions", item], "DELETE")).toBeNull();
    expect(mentoringPath(["organizations", org, "private-notes"], "GET")).toBeNull();
  });
});
