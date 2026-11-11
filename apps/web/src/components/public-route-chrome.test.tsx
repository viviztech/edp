import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useSelectedLayoutSegment } from "next/navigation";
import { PublicRouteChrome } from "./public-route-chrome";

vi.mock("next/navigation", () => ({ useSelectedLayoutSegment: vi.fn() }));
afterEach(cleanup);

describe("locale route chrome", () => {
  function renderChrome(segment: string | null) {
    vi.mocked(useSelectedLayoutSegment).mockReturnValue(segment);
    render(<PublicRouteChrome header={<header>Public navigation</header>} footer={<footer>Public footer</footer>}>
      <div>Page content</div>
    </PublicRouteChrome>);
  }

  it("shows public navigation and footer on public routes", () => {
    renderChrome("pages");
    expect(screen.getByText("Public navigation")).toBeTruthy();
    expect(screen.getByText("Public footer")).toBeTruthy();
    expect(screen.getByText("Page content")).toBeTruthy();
  });

  it("does not show public chrome on the admin route", () => {
    renderChrome("admin");
    expect(screen.queryByText("Public navigation")).toBeNull();
    expect(screen.queryByText("Public footer")).toBeNull();
    expect(screen.getByText("Page content")).toBeTruthy();
  });
});
