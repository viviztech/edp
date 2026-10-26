import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { ReadonlyURLSearchParams, usePathname, useSearchParams } from "next/navigation";
import { PublicNavigation } from "./public-navigation";

vi.mock("next/navigation", async (importOriginal) => ({
  ...await importOriginal<typeof import("next/navigation")>(),
  usePathname: vi.fn(), useSearchParams: vi.fn(),
}));

beforeEach(() => {
  vi.mocked(usePathname).mockReturnValue("/en");
  vi.mocked(useSearchParams).mockReturnValue(new ReadonlyURLSearchParams());
});
afterEach(cleanup);

const props = {
  locale: "en" as const,
  navigationLabel: "Public navigation",
  labels: {
    home: "Home", program: "The program", support: "Explore", updates: "Updates",
    contact: "Contact", apply: "Apply", account: "Account", language: "Tamil",
    news: "News", events: "Events", faq: "FAQ",
  },
  program: [{ title: "About", href: "/en/pages/about" }],
  support: [{ title: "Resources", href: "/en/pages/resources" }],
};

describe("public navigation dropdowns", () => {
  it("opens on hover and closes when the pointer leaves the menu", () => {
    render(<PublicNavigation {...props} />);
    const trigger = screen.getByRole("button", { name: "The program" });
    const group = trigger.closest(".site-nav-group")!;
    expect(trigger.getAttribute("aria-expanded")).toBe("false");

    fireEvent.mouseEnter(group);
    expect(trigger.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByRole("link", { name: "About" }).getAttribute("href")).toBe("/en/pages/about");

    fireEvent.mouseLeave(group);
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
  });

  it("toggles by touch and closes with Escape", () => {
    render(<PublicNavigation {...props} />);
    const trigger = screen.getByRole("button", { name: "Explore" });
    const group = trigger.closest(".site-nav-group")!;

    fireEvent.touchStart(trigger);
    fireEvent.click(trigger, { detail: 1 });
    expect(trigger.getAttribute("aria-expanded")).toBe("true");

    fireEvent.touchStart(trigger);
    fireEvent.click(trigger, { detail: 1 });
    expect(trigger.getAttribute("aria-expanded")).toBe("false");

    fireEvent.click(trigger, { detail: 0 });
    expect(trigger.getAttribute("aria-expanded")).toBe("true");
    fireEvent.keyDown(group, { key: "Escape" });
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
  });
});

describe("language navigation", () => {
  const organization = "123e4567-e89b-42d3-a456-426614174000";
  const cycle = "123e4567-e89b-42d3-a456-426614174001";

  it("retains the application path and validated intake context without carrying tokens or return URLs", () => {
    vi.mocked(usePathname).mockReturnValue("/en/applications");
    vi.mocked(useSearchParams).mockReturnValue(new ReadonlyURLSearchParams({ organization, cycle, token: "private", returnTo: "https://example.test", query: "ignored" }));
    render(<PublicNavigation {...props} />);
    const link = screen.getByRole("link", { name: "Tamil" });
    expect(link.getAttribute("href")).toBe(`/ta/applications?organization=${organization}&cycle=${cycle}`);
    expect(link.getAttribute("lang")).toBe("ta");
  });

  it("preserves a staff detail path and its organization when returning to English", () => {
    vi.mocked(usePathname).mockReturnValue("/ta/admin/reports");
    vi.mocked(useSearchParams).mockReturnValue(new ReadonlyURLSearchParams({ organization }));
    render(<PublicNavigation {...props} locale="ta" labels={{ ...props.labels, language: "English" }} />);
    expect(screen.getByRole("link", { name: "English" }).getAttribute("href")).toBe(`/en/admin/reports?organization=${organization}`);
  });

  it.each([
    `organization=${organization}&organization=${cycle}&cycle=${cycle}`,
    `organization=invalid&cycle=${cycle}`,
    `cycle=${cycle}`,
  ])("discards ambiguous or invalid organization context: %s", (query) => {
    vi.mocked(usePathname).mockReturnValue("/en/applications");
    vi.mocked(useSearchParams).mockReturnValue(new ReadonlyURLSearchParams(query));
    render(<PublicNavigation {...props} />);
    expect(screen.getByRole("link", { name: "Tamil" }).getAttribute("href")).toBe("/ta/applications");
  });

  it("lets the existing capture-phase unsaved-edit guard cancel a language change", () => {
    vi.mocked(usePathname).mockReturnValue("/en/business-plan");
    render(<PublicNavigation {...props} />);
    const guard = vi.fn((event: Event) => event.preventDefault());
    document.addEventListener("click", guard, true);
    try {
      expect(fireEvent.click(screen.getByRole("link", { name: "Tamil" }))).toBe(false);
      expect(guard).toHaveBeenCalledOnce();
      expect(screen.getByRole("link", { name: "Tamil" }).getAttribute("href")).toBe("/ta/business-plan");
    } finally {
      document.removeEventListener("click", guard, true);
    }
  });
});
