import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import Account from "./view";
import { authMessages } from "../../../lib/auth-messages";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("account workspace navigation", () => {
  it("offers participant and learning links only for the selected organization's permissions", async () => {
    vi.stubGlobal("fetch", vi.fn(async (url: string) => ({
      ok: true,
      json: async () => url === "/api/session/me"
        ? { display_name: "Test participant", grants: [
            { organization_id: "org-one", organization_name: "Program one", permissions: ["system.access", "participant.self", "lms.learn", "mentoring.view"] },
            { organization_id: "org-two", organization_name: "Program two", permissions: ["system.access"] },
          ] }
        : [],
    })));
    render(<Account locale="en" text={authMessages.en} selfServiceEnabled={false} />);
    expect((await screen.findByRole("link", { name: "My program" })).getAttribute("href")).toBe("/en/participant?organization=org-one");
    expect(screen.getByRole("link", { name: "My learning" }).getAttribute("href")).toBe("/en/learning?organization=org-one");
    expect(screen.getByRole("link", { name: "Staff workspace" }).getAttribute("href")).toBe("/en/admin?organization=org-two");
    expect(screen.queryByRole("link", { name: "Application draft" })).toBeNull();
  });
});
