import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import type { IntakeContext, IntakeSearch } from "../../../lib/intake-context";
import AccountPage from "./page";
vi.mock("next/navigation", () => ({ notFound: () => { throw new Error("not found"); } }));
vi.mock("./view", () => ({ default: ({ locale, intake }: { locale: string; intake: IntakeContext }) => <div data-testid="account" data-locale={locale} data-context={JSON.stringify(intake)} /> }));
const organization = "11111111-1111-4111-8111-111111111111";
const cycle = "22222222-2222-4222-8222-222222222222";
afterEach(() => { cleanup(); vi.unstubAllEnvs(); });
const page = (query: IntakeSearch) => AccountPage({ params: Promise.resolve({ locale: "ta" }), searchParams: Promise.resolve(query) });

describe("account server intake boundary", () => {
  it("preserves a valid chosen intake and ignores external returnTo input", async () => {
    render(await page({ organization, cycle, returnTo: "https://outside.example/" }));
    expect(screen.getByTestId("account").getAttribute("data-locale")).toBe("ta");
    expect(JSON.parse(screen.getByTestId("account").getAttribute("data-context")!)).toEqual({ organization, cycle });
    expect(screen.getByRole("main").getAttribute("tabindex")).toBe("-1");
  });
  it("uses the configured public organization when none was explicitly selected", async () => {
    vi.stubEnv("PUBLIC_ORGANIZATION_ID", organization);
    render(await page({ cycle }));
    expect(JSON.parse(screen.getByTestId("account").getAttribute("data-context")!)).toEqual({ organization, cycle });
  });
  it.each([
    { organization: "//outside.example", cycle }, { organization: [organization, organization] },
    { organization, cycle: "../intake" }, { organization, cycle: [cycle, cycle] },
  ])("rejects malformed or repeated explicit context without silently substituting an intake: %s", async query => {
    vi.stubEnv("PUBLIC_ORGANIZATION_ID", organization);
    await expect(page(query)).rejects.toThrow("not found");
  });
  it("rejects a cycle without any resolved organization", async () => {
    vi.stubEnv("PUBLIC_ORGANIZATION_ID", "");
    await expect(page({ cycle })).rejects.toThrow("not found");
  });
});
