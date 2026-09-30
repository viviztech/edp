import { describe, expect, it } from "vitest";
import { learningPath } from "./learning-security";

const org = "123e4567-e89b-42d3-a456-426614174000";
const course = "123e4567-e89b-42d3-a456-426614174001";
const material = "123e4567-e89b-42d3-a456-426614174002";

describe("learning BFF allowlist", () => {
  it("allows the explicit staff, trainer, learner and material routes", () => {
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
    expect(learningPath(["organizations", org, "trainer-delivery"], "GET"))
      .toBe(`/courses/organizations/${org}/trainer-delivery`);
    expect(learningPath(["organizations", org, "my-learning", course, "start"], "POST"))
      .toBe(`/courses/organizations/${org}/my-learning/${course}/start`);
    expect(learningPath([
      "organizations", org, "my-learning", course, "materials", material, "access",
    ], "POST")).not.toBeNull();
    expect(learningPath([
      "organizations", org, "trainer-delivery", course, "materials", material, "access",
    ], "POST")).not.toBeNull();
    expect(learningPath([
      "organizations", org, "material-delivery", "payload.signature",
    ], "GET")).not.toBeNull();
    expect(learningPath(["organizations", org, "prerequisites"], "POST")).not.toBeNull();
    expect(learningPath(["organizations", org, course, "completion-rule"], "POST")).not.toBeNull();
    expect(learningPath([
      "organizations", org, "my-learning", course, "lessons", course, "complete",
    ], "POST")).not.toBeNull();
  });

  it("rejects traversal, malformed tokens, deletes and unknown commands", () => {
    expect(learningPath(["organizations", org, "..", "auth"], "GET")).toBeNull();
    expect(learningPath(["organizations", org, "material-delivery", "bad.token.extra"], "GET")).toBeNull();
    expect(learningPath(["organizations", org, course], "DELETE")).toBeNull();
    expect(learningPath(["organizations", org, course, "complete"], "POST")).toBeNull();
  });
});
