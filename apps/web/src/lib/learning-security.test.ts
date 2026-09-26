import { describe, expect, it } from "vitest";
import { learningPath } from "./learning-security";

const org = "123e4567-e89b-42d3-a456-426614174000";
const course = "123e4567-e89b-42d3-a456-426614174001";

describe("learning BFF allowlist", () => {
  it("allows the explicit staff and learner routes", () => {
    expect(learningPath(["organizations", org, "catalog"], "GET"))
      .toBe(`/courses/organizations/${org}/catalog`);
    expect(learningPath(["organizations", org], "POST"))
      .toBe(`/courses/organizations/${org}`);
    expect(learningPath(["organizations", org, "modules"], "POST"))
      .toBe(`/courses/organizations/${org}/modules`);
    expect(learningPath(["organizations", org, course, "publish"], "POST"))
      .toBe(`/courses/organizations/${org}/${course}/publish`);
    expect(learningPath(["organizations", org, "my-learning"], "GET"))
      .toBe(`/courses/organizations/${org}/my-learning`);
    expect(learningPath(["organizations", org, "my-learning", course, "start"], "POST"))
      .toBe(`/courses/organizations/${org}/my-learning/${course}/start`);
  });

  it("rejects traversal, deletes and unknown commands", () => {
    expect(learningPath(["organizations", org, "..", "auth"], "GET")).toBeNull();
    expect(learningPath(["organizations", org, course], "DELETE")).toBeNull();
    expect(learningPath(["organizations", org, course, "complete"], "POST")).toBeNull();
  });
});
