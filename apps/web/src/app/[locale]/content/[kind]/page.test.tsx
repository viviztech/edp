import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { publicEditorial } from "../../../../lib/public-editorial";
import EditorialList from "./page";
vi.mock("../../../../lib/public-editorial", () => ({ publicEditorial: vi.fn() }));
vi.mock("next/navigation", () => ({ notFound: () => { throw new Error("not found"); } }));
const cursor = "11111111-1111-4111-8111-111111111111";
const next = "22222222-2222-4222-8222-222222222222";
afterEach(() => { cleanup(); vi.resetAllMocks(); });
describe("public editorial pagination", () => {
  it("preserves Tamil and content type in first and next links", async () => {
    vi.mocked(publicEditorial).mockResolvedValue({ items: [], next_cursor: next });
    render(await EditorialList({ params: Promise.resolve({ locale: "ta", kind: "event" }), searchParams: Promise.resolve({ cursor }) }));
    expect(publicEditorial).toHaveBeenCalledWith("event", "ta", cursor);
    expect(screen.getByRole("link", { name: "முதல் பக்கம்" }).getAttribute("href")).toBe("/ta/content/event");
    expect(screen.getByRole("link", { name: "அடுத்த பக்கம்" }).getAttribute("href")).toBe(`/ta/content/event?cursor=${next}`);
    expect(screen.getByRole("main").getAttribute("tabindex")).toBe("-1");
  });
  it.each([{ cursor: "https://outside.example" }, { cursor: [cursor, cursor] }, { limit: "1000" }])("rejects malformed or unsupported search input %s", async search => {
    await expect(EditorialList({ params: Promise.resolve({ locale: "en", kind: "news" }), searchParams: Promise.resolve(search) })).rejects.toThrow("not found");
    expect(publicEditorial).not.toHaveBeenCalled();
  });
  it("distinguishes an unavailable page from an empty collection and offers restart after a cursor error", async () => {
    vi.mocked(publicEditorial).mockRejectedValue(new Error("unavailable"));
    render(await EditorialList({ params: Promise.resolve({ locale: "en", kind: "news" }), searchParams: Promise.resolve({ cursor }) }));
    expect(screen.getByRole("alert").textContent).toContain("could not be loaded");
    expect(screen.getByRole("link", { name: "First page" }).getAttribute("href")).toBe("/en/content/news");
    expect(screen.queryByRole("link", { name: "Next page" })).toBeNull();
  });
});
