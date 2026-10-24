import { describe, expect, it } from "vitest";
import { participantNotificationPath as path, participantNotificationQuery as query } from "./participant-notification-security";
const id = "11111111-1111-4111-8111-111111111111", root = ["organizations", id];
describe("participant notification gateway boundaries", () => {
  it("allows only the recipient inbox, preference and explicit read commands", () => {
    expect(path([...root, "mine"], "GET")).toBe(`/participant-notifications/organizations/${id}/mine`);
    expect(path([...root, "preference"], "GET")).toBeTruthy(); expect(path([...root, "preference"], "POST")).toBeTruthy();
    expect(path([...root, id, "read"], "POST")).toBeTruthy();
    for (const parts of [[...root, "operations", "failed"], [...root, id], [...root, "..", "auth"], ["organizations", "invalid", "mine"]]) expect(path(parts, "GET")).toBeNull();
    expect(path([...root, "mine"], "POST")).toBeNull(); expect(path([...root, "preference"], "PATCH")).toBeNull();
  });
  it("accepts bounded unique list pagination and no other query on any route", () => {
    const list = path([...root, "mine"], "GET")!;
    expect(query(list, "GET", new URLSearchParams())).toBe("limit=25");
    expect(query(list, "GET", new URLSearchParams({ cursor: id, limit: "100" }))).toBe(`cursor=${id}&limit=100`);
    for (const invalid of ["limit=0", "limit=101", "limit=1&limit=2", "cursor=", "cursor=invalid", `cursor=${id}&cursor=${id}`, "topic=enrollment_created", `recipient_id=${id}`]) expect(query(list, "GET", new URLSearchParams(invalid))).toBeNull();
    expect(query(`/participant-notifications/organizations/${id}/preference`, "POST", new URLSearchParams("limit=1"))).toBeNull();
  });
});
