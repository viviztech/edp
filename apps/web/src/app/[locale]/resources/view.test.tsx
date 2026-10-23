import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import PublicResources from "./view";
import { resource } from "../knowledge/test-fixtures";
import { words } from "../knowledge/content";

afterEach(cleanup);
describe("anonymous resource discovery", () => {
  it("renders official evidence, GET filters and pagination without participant actions", () => {
    render(<PublicResources locale="en" failed={false} filters={{ kind: "funding", q: "equipment" }}
      data={{ items: [resource({ availability: "upcoming", official_url: "http://example.gov.in/source" })], next_cursor: "22222222-2222-4222-8222-222222222223" }} />);
    const article = screen.getByRole("article", { name: "Synthetic funding" });
    expect(within(article).getByText("Upcoming")).toBeTruthy();
    expect(within(article).getByRole("link", { name: "Official source" }).getAttribute("href")).toBe("http://example.gov.in/source");
    expect(screen.queryByRole("button", { name: "Save resource" })).toBeNull();
    expect((screen.getByLabelText("Search resources") as HTMLInputElement).value).toBe("equipment");
    const next = screen.getByRole("link", { name: "Load more" }).getAttribute("href");
    expect(next).toContain("kind=funding"); expect(next).toContain("cursor=");
  });
  it("does not render unsafe source links and distinguishes service failure from an empty catalog", () => {
    const view = render(<PublicResources locale="en" failed={false} filters={{}} data={{ items: [resource({ official_url: "javascript:alert(1)" })], next_cursor: null }} />);
    expect(screen.queryByRole("link", { name: "Official source" })).toBeNull(); view.unmount();
    render(<PublicResources locale="ta" failed filters={{}} data={null} />);
    expect(screen.getByRole("status").textContent).toBe(words.ta.error);
    expect(screen.queryByText(words.ta.empty)).toBeNull();
  });
});
