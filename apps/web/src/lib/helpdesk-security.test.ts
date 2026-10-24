import { describe, expect, it } from "vitest";
import { helpdeskPath, helpdeskQuery } from "./helpdesk-security";
const org = "11111111-1111-4111-8111-111111111111";
const ticket = "22222222-2222-4222-8222-222222222222";
describe("helpdesk fixed routing", () => {
  it("admits specific method paths without allowing traversal or arbitrary upstream access", () => {
    expect(helpdeskPath(["organizations", org, "tickets", ticket, "reopen"], "POST")).toContain(`/tickets/${ticket}/reopen`);
    expect(helpdeskPath(["organizations", org, "tickets", ticket, "attachments", ticket], "GET")).toContain("/attachments/");
    for (const path of [["..", "auth"], ["organizations", org, "users"], ["organizations", "invalid", "tickets"], ["organizations", org, "tickets", ticket, "attachment"]]) expect(helpdeskPath(path, "GET")).toBeNull();
    expect(helpdeskPath(["organizations", org, "tickets", ticket], "PATCH")).toBeNull();
  });
  it("bounds filters/cursors and rejects duplicate or unsupported parameters", () => {
    expect(helpdeskQuery(new URLSearchParams("queue=unassigned&status=open&category=banking&priority=high&limit=100"))).toContain("queue=unassigned");
    for (const query of ["limit=101", "status=deleted", "queue=all", "cursor=invalid", "status=open&status=closed", "user=other", "limit=0", "limit=01"]) expect(helpdeskQuery(new URLSearchParams(query))).toBeNull();
    expect(helpdeskQuery(new URLSearchParams("constructor=value"))).toBeNull();
  });
  it("closes raw bytes and staged metadata to exact typed file routes and paging only",()=>{
    const files=["organizations",org,"tickets",ticket,"files"];
    for(const [method,suffix] of [["GET",[]],["POST",[]],["GET",[ticket]],["DELETE",[ticket]],["PUT",[ticket,"content"]],["GET",[ticket,"content"]]] as const)expect(helpdeskPath([...files,...suffix],method)).toContain("/files");
    for(const [method,suffix] of [["POST",[ticket,"scan"]],["POST",[ticket,"publish"]],["DELETE",[ticket,"content"]],["PUT",[]]] as const)expect(helpdeskPath([...files,...suffix],method)).toBeNull();
    expect(helpdeskQuery(new URLSearchParams(`limit=25&cursor=${ticket}`),files,"GET")).toContain("limit=25");
    for(const query of ["internal=true","owner=other","queue=organization","status=clean","cursor=bad","limit=1&limit=2"])expect(helpdeskQuery(new URLSearchParams(query),files,"GET")).toBeNull();
    expect(helpdeskQuery(new URLSearchParams("limit=25"),[...files,ticket,"content"],"GET")).toBeNull();
    expect(helpdeskQuery(new URLSearchParams("limit=25"),files,"POST")).toBeNull();
  });
});
