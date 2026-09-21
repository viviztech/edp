import { describe, expect, it } from "vitest";
import { notificationPath } from "./notification-security";

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
