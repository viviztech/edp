import { describe, expect, it } from "vitest";
import { learningPath, learningQuery } from "./learning-security";

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
    expect(learningPath(["organizations", org, "assignments"], "POST")).not.toBeNull();
    expect(learningPath(["organizations", org, "certificate-templates"], "POST")).not.toBeNull();
    expect(learningPath([
      "organizations", org, "certificate-templates", course, "publish",
    ], "POST")).not.toBeNull();
    expect(learningPath(["organizations", org, "certificates", "issue"], "POST"))
      .not.toBeNull();
    expect(learningPath([
      "organizations", org, "certificates", course, "revoke",
    ], "POST")).not.toBeNull();
    expect(learningPath(["organizations", org, "quizzes"], "POST")).not.toBeNull();
    expect(learningPath(["organizations", org, "quiz-questions"], "POST")).not.toBeNull();
    expect(learningPath(["organizations", org, "quiz-choices"], "POST")).not.toBeNull();
    expect(learningPath([
      "organizations", org, "my-learning", course, "quizzes", course, "attempts",
    ], "POST")).not.toBeNull();
    expect(learningPath([
      "organizations", org, "my-learning", course, "assignments", course, "submissions",
    ], "POST")).not.toBeNull();
    expect(learningPath([
      "organizations", org, "trainer-delivery", course,
      "assignment-submissions", course, "grade",
    ], "POST")).not.toBeNull();
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

  it("limits file operations to typed assignment, staff-review and material bindings", () => {
    const owner = ["organizations", org, "my-learning", course, "assignments", material, "files"];
    const author = ["organizations", org, "courses", course, "material-files"];
    for (const path of [owner, author]) {
      expect(learningPath(path, "GET")).not.toBeNull();
      expect(learningPath([...path, material], "GET")).not.toBeNull();
      expect(learningPath([...path, material], "DELETE")).not.toBeNull();
      expect(learningPath([...path, material, "content"], "GET")).not.toBeNull();
      expect(learningPath([...path, material, "content"], "PUT")).not.toBeNull();
      expect(learningPath([...path, material, "content"], "POST")).toBeNull();
      expect(learningPath([...path, material, "content"], "DELETE")).toBeNull();
      expect(learningPath([...path, "..", "content"], "PUT")).toBeNull();
    }
    const review = ["organizations", org, "trainer-delivery", course, "assignment-submissions", material, "files"];
    expect(learningPath(review, "GET")).not.toBeNull();
    expect(learningPath([...review, material, "content"], "GET")).not.toBeNull();
    expect(learningPath([...review, material, "content"], "PUT")).toBeNull();
    expect(learningPath([...review, material], "DELETE")).toBeNull();
  });

  it("accepts only bounded single-value material pagination and no extra file queries", () => {
    const path = learningPath(["organizations", org, "courses", course, "material-files"], "GET")!;
    expect(learningQuery(path, new URLSearchParams(`limit=100&cursor=${material}`))).toBe(true);
    expect(learningQuery(path, new URLSearchParams())).toBe(true);
    for (const query of ["limit=0", "limit=101", "limit=01", "limit=1&limit=2", "cursor=../other", "person_id=other", "limit=2&org=other"]) {
      expect(learningQuery(path, new URLSearchParams(query))).toBe(false);
    }
    expect(learningQuery(`${path}/${material}/content`, new URLSearchParams("limit=1"))).toBe(false);
  });
});
