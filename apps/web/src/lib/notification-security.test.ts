import { describe, expect, it } from "vitest";
import { notificationPath, notificationQuery } from "./notification-security";

const id = "11111111-1111-4111-8111-111111111111";

describe("notificationPath", () => {
  it("allows only the self-service inbox and preference routes", () => {
    expect(notificationPath(["organizations", id, "mine"], "GET")).toContain("/notifications/");
    expect(notificationPath(["organizations", id, "preference"], "POST")).toContain("/notifications/");
    expect(notificationPath(["organizations", id, id, "read"], "POST")).toContain("/notifications/");
  });
  it("rejects arbitrary or privileged routes", () => {
    expect(notificationPath(["organizations", id, "all"], "GET")).toBeNull();
    expect(notificationPath(["organizations", id, id, "read"], "GET")).toBeNull();
    expect(notificationPath(["organizations", id, "mine"], "DELETE")).toBeNull();
  });
});


describe("notificationQuery", () => {
  const mine = "/notifications/organizations/" + id + "/mine";
  const preference = "/notifications/organizations/" + id + "/preference";
  it("allows a bounded inbox cursor and a separate follow-up preference", () => {
    expect(notificationQuery(mine, "GET", new URLSearchParams({ cursor: id }))).toContain("limit=25");
    expect(notificationQuery(preference, "POST", new URLSearchParams({ topic: "followup_due" }))).toBe("topic=followup_due");
  });
  it("rejects arbitrary topics, misplaced cursors and unknown parameters", () => {
    expect(notificationQuery(preference, "POST", new URLSearchParams({ topic: "admin" }))).toBeNull();
    expect(notificationQuery(preference, "POST", new URLSearchParams({ cursor: id }))).toBeNull();
    expect(notificationQuery(mine, "GET", new URLSearchParams({ topic: "followup_due" }))).toBeNull();
    expect(notificationQuery(mine, "GET", new URLSearchParams({ limit: "1000" }))).toBeNull();
    expect(notificationQuery(preference, "GET", new URLSearchParams("topic=followup_due&topic=lead_assignment"))).toBeNull();
    expect(notificationQuery(mine, "GET", new URLSearchParams("cursor="))).toBeNull();
  });
});
