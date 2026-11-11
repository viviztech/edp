import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import ProgramWorkspace from "./view";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("program workspace navigation", () => {
  it.each(["en", "ta"] as const)("links to every section in %s", async (locale) => {
    vi.stubGlobal("fetch", vi.fn(async (url: string) => ({
      ok: true,
      json: async () => url.includes("application-definitions") ? { items: [] } : {
        programs: [], centers: [], cohorts: [], cycles: [], enrollment_candidates: [],
        participants: [], enrollments: [], sessions: [], staff_assignments: [],
      },
    })));
    render(<ProgramWorkspace org="org" locale={locale} permissions={[]} />);
    const nav = screen.getByRole("navigation", { name: locale === "ta" ? "பக்கப் பிரிவுகள்" : "On this page" });
    const links = within(nav).getAllByRole("link");
    expect(links).toHaveLength(8);
    for (const link of links) {
      const target = link.getAttribute("href");
      expect(target).toMatch(/^#[a-z-]+$/);
      expect(document.getElementById(target!.slice(1))).not.toBeNull();
    }
    await waitFor(() => expect(screen.getByRole("navigation", { name: locale === "ta" ? "பக்கப் பிரிவுகள்" : "On this page" }).closest(".program-workspace")?.getAttribute("aria-busy")).toBe("false"));
  });
});
