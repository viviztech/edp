import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { PublicNavigation } from "./public-navigation";

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
