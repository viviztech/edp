import { describe, expect, it, vi } from "vitest";
vi.mock("./public-navigation", () => ({ publicNavigation: vi.fn().mockResolvedValue([]) }));
import { render, screen } from "@testing-library/react";
import { authMessages } from "./auth-messages";
import { isLocale, messages } from "./messages";
import Home from "../app/[locale]/page";

describe("localization foundation", () => {
  it("keeps Tamil and English keys aligned and rejects unsupported routes", () => {
    expect(Object.keys(messages.en).sort()).toEqual(Object.keys(messages.ta).sort());
    expect(Object.keys(authMessages.en).sort()).toEqual(Object.keys(authMessages.ta).sort());
    expect(isLocale("fr")).toBe(false);
    expect(isLocale("ta")).toBe(true);
  });
  it("renders the actual Tamil public shell", async () => {
    render(await Home({ params: Promise.resolve({ locale: "ta" }) }));
    expect(screen.getByText(messages.ta.availability)).toBeTruthy();
  });
});
