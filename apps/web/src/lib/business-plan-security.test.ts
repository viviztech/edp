import { describe, expect, it } from "vitest";
import { businessPlanPath } from "./business-plan-security";

const org = "123e4567-e89b-42d3-a456-426614174000";
const enrollment = "123e4567-e89b-42d3-a456-426614174001";

describe("business-plan BFF allowlist", () => {
  it("allows only the participant draft routes", () => {
    expect(businessPlanPath(["organizations", org, "mine"], "GET"))
      .toBe(`/business-plans/organizations/${org}/mine`);
    expect(businessPlanPath(["organizations", org, "enrollments", enrollment], "POST"))
      .toBe(`/business-plans/organizations/${org}/enrollments/${enrollment}`);
    expect(businessPlanPath(["organizations", org, "enrollments", enrollment, "sections"], "POST"))
      .toBe(`/business-plans/organizations/${org}/enrollments/${enrollment}/sections`);
    expect(businessPlanPath(["organizations", org, "enrollments", enrollment, "submit"], "POST"))
      .toBe(`/business-plans/organizations/${org}/enrollments/${enrollment}/submit`);
    expect(businessPlanPath(["organizations", org, "assigned"], "GET"))
      .toBe(`/business-plans/organizations/${org}/assigned`);
    expect(businessPlanPath(["organizations", org, "submissions", enrollment, "review"], "POST"))
      .toBe(`/business-plans/organizations/${org}/submissions/${enrollment}/review`);
  });

  it("rejects traversal, unsupported methods and review paths", () => {
    expect(businessPlanPath(["organizations", org, "..", "auth"], "GET")).toBeNull();
    expect(businessPlanPath(["organizations", org, "enrollments", enrollment], "DELETE")).toBeNull();
    expect(businessPlanPath(["organizations", org, "reviews"], "POST")).toBeNull();
  });
});
