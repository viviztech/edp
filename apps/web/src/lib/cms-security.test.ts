import {describe,it,expect} from "vitest";
import {cmsPath, cmsQuery} from "./cms-security";
import {cmsMessages} from "./cms-messages";
describe("CMS boundary",()=>{
 const id="11111111-1111-1111-1111-111111111111";
 it("allows only explicit editorial routes",()=>{expect(cmsPath(["organizations",id,"pages",id,"translations","en","publish"],"POST")).toContain("/cms/");for(const p of [["https:","evil.example"],["organizations",id,"pages","..","auth"],["organizations",id,"pages",id,"translations","en","delete"]])expect(cmsPath(p,"POST")).toBeNull();expect(cmsPath(["organizations",id,"pages"],"DELETE")).toBeNull();});
 it("provides parity for every CMS label",()=>expect(Object.keys(cmsMessages.ta).sort()).toEqual(Object.keys(cmsMessages.en).sort()));
 it("allows exact editorial lifecycle and typed media routes", () => {
  for (const [path, method] of [[`organizations/${id}/editorial`, "GET"], [`organizations/${id}/editorial/${id}`, "PATCH"], [`organizations/${id}/editorial/${id}/publish`, "POST"], [`organizations/${id}/editorial/${id}/archive`, "POST"], [`organizations/${id}/editorial/${id}/restore`, "POST"], [`organizations/${id}/assets`, "GET"]]) expect(cmsPath(path.split("/"), method)).toBe(`/cms/${path}`);
  for(const suffix of ["source","prepare","publish","revoke"]) expect(cmsPath(["organizations",id,"assets",id,suffix],"POST")).toBe(`/cms/organizations/${id}/assets/${id}/${suffix}`);
  expect(cmsPath(["organizations",id,"assets",id,"source","content"],"PUT")).toContain("/source/content");
  for (const [path, method] of [[`organizations/${id}/assets/${id}/scan`, "POST"], [`organizations/${id}/assets/${id}/content`, "PUT"], [`organizations/${id}/editorial/${id}`, "DELETE"], [`organizations/${id}/enquiries`, "GET"]]) expect(cmsPath(path.split("/"), method)).toBeNull();
 });
 it("bounds collection queries and rejects unknown, duplicate and misplaced queries", () => {
  const editorial = ["organizations", id, "editorial"];
  expect(cmsQuery(editorial, "GET", new URLSearchParams(`kind=event&locale=ta&cursor=${id}&limit=100`))).toBe(`kind=event&locale=ta&cursor=${id}&limit=100`);
  expect(cmsQuery(editorial, "GET", new URLSearchParams())).toBe("limit=25");
  expect(cmsQuery(editorial, "GET", new URLSearchParams("kind=news&locale=ta&slug=exact-address&limit=1"))).toBe("kind=news&locale=ta&slug=exact-address&limit=1");
  for (const query of ["limit=101", "limit=0", "limit=01", "kind=other", "locale=fr", "locale=en&locale=ta", "cursor=../admin", "limit=25&limit=25", "returnTo=https://example.com/"]) expect(cmsQuery(editorial, "GET", new URLSearchParams(query))).toBeNull();
  expect(cmsQuery([...editorial, id], "GET", new URLSearchParams("limit=25"))).toBeNull();
  expect(cmsQuery(editorial, "POST", new URLSearchParams("limit=25"))).toBeNull();
  expect(cmsQuery(["organizations", id, "assets"], "GET", new URLSearchParams("kind=news"))).toBeNull();
  for (const value of ["../address", "Bad", "", "a".repeat(121)]) expect(cmsQuery(editorial, "GET", new URLSearchParams({ slug: value }))).toBeNull();
  expect(cmsQuery(editorial, "GET", new URLSearchParams("slug=first&slug=second"))).toBeNull();
 });
});
