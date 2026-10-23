import { describe, expect, it } from "vitest";
import { filePolicyPath, filePolicyQuery } from "./file-policy-security";
const org = "11111111-1111-4111-8111-111111111111", id = "22222222-2222-4222-8222-222222222222";
const parts = ["organizations", org, "policies"];
describe("closed file-policy surface", () => {
  it("allows policy administration without any generic file or byte capability", () => {
    expect(filePolicyPath(parts, "GET")).toBe(`/files/organizations/${org}/policies`);
    expect(filePolicyPath([...parts, id, "publish"], "POST")).toBe(`/files/organizations/${org}/policies/${id}/publish`);
    expect(filePolicyPath([...parts, id], "PATCH")).toBe(`/files/organizations/${org}/policies/${id}`);
    for (const path of [["organizations", org, "objects"], [...parts, id, "upload"], [...parts, id, "download"], [...parts, id, "activate"], [...parts, "..", "files"]]) expect(filePolicyPath(path, "POST")).toBeNull();
    expect(filePolicyPath([...parts, id], "DELETE")).toBeNull();
  });
  it("bounds unique list filters and disallows queries on detail or mutation paths", () => {
    expect(filePolicyQuery(parts, "GET", new URLSearchParams("purpose=application_document"))).toBe("purpose=application_document&limit=25");
    for (const query of ["limit=0", "limit=101", "purpose=identity", "purpose=cms_asset&purpose=lms_material", "cursor=../files", "collection_enabled=true", "state=published"]) expect(filePolicyQuery(parts, "GET", new URLSearchParams(query))).toBeNull();
    expect(filePolicyQuery([...parts, id], "GET", new URLSearchParams("limit=1"))).toBeNull();
    expect(filePolicyQuery(parts, "POST", new URLSearchParams("purpose=cms_asset"))).toBeNull();
  });
});
