import {describe,it,expect} from "vitest";
import {cmsPath} from "./cms-security";
import {cmsMessages} from "./cms-messages";
describe("CMS boundary",()=>{
 const id="11111111-1111-1111-1111-111111111111";
 it("allows only explicit editorial routes",()=>{expect(cmsPath(["organizations",id,"pages",id,"translations","en","publish"],"POST")).toContain("/cms/");for(const p of [["https:","evil.example"],["organizations",id,"pages","..","auth"],["organizations",id,"pages",id,"translations","en","delete"]])expect(cmsPath(p,"POST")).toBeNull();expect(cmsPath(["organizations",id,"pages"],"DELETE")).toBeNull();});
 it("provides parity for every CMS label",()=>expect(Object.keys(cmsMessages.ta).sort()).toEqual(Object.keys(cmsMessages.en).sort()));
});
