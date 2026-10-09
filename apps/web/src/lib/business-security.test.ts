import { describe, expect, it } from "vitest";
import { businessPath } from "./business-security";

const org = "123e4567-e89b-42d3-a456-426614174000";
const item = "123e4567-e89b-42d3-a456-426614174001";

describe("business BFF allowlist", () => {
  it("allows only the expected participant and staff routes", () => {
    expect(businessPath(["organizations", org, "mine"], "GET"))
      .toBe(`/businesses/organizations/${org}/mine`);
    expect(businessPath(["organizations", org, "staff"], "GET"))
      .toBe(`/businesses/organizations/${org}/staff`);
    expect(businessPath(["organizations", org, "profiles"], "POST"))
      .toBe(`/businesses/organizations/${org}/profiles`);
    expect(businessPath(["organizations", org, "profiles", item, "update"], "POST"))
      .toBe(`/businesses/organizations/${org}/profiles/${item}/update`);
    expect(businessPath(["organizations", org, "follow-ups", item, "outcome"], "POST"))
      .toBe(`/businesses/organizations/${org}/follow-ups/${item}/outcome`);
    expect(businessPath(["organizations", org, "policy"], "POST"))
      .toBe(`/businesses/organizations/${org}/policy`);
  });
  it("rejects traversal and unsupported methods", () => {
    expect(businessPath(["organizations", org, "..", "auth"], "GET")).toBeNull();
    expect(businessPath(["organizations", org, "profiles", item], "DELETE")).toBeNull();
  });
});
