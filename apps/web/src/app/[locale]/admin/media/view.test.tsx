import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import MediaMetadata from "./view";
import { mediaAdminMessages } from "../../../../lib/media-admin-messages";

const org = "11111111-1111-4111-8111-111111111111";
const cursor = "22222222-2222-4222-8222-222222222222";
const asset = { id: cursor, filename: "synthetic.pdf", title: "Synthetic media", media_type: "application/pdf", byte_size: 1000, scan_status: "clean", visibility: "public", public_url: "https://outside.example/unbacked-file" };
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("media metadata overview", () => {
  it("shows recorded metadata in Tamil without exposing file or publication actions", async () => {
    const mock = vi.fn().mockResolvedValue(json({ items: [asset], next_cursor: null })); vi.stubGlobal("fetch", mock);
    await act(async () => { render(<MediaMetadata org={org} locale="ta" />); });
    expect(screen.getByText("synthetic.pdf")).toBeTruthy();
    expect(screen.getByText(mediaAdminMessages.ta.clean)).toBeTruthy();
    expect(screen.getByText(mediaAdminMessages.ta.boundary)).toBeTruthy();
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.queryByLabelText(/upload/i)).toBeNull();
    expect(screen.getAllByRole("button")).toHaveLength(1);
    expect(mock.mock.calls[0][1]).toEqual({ cache: "no-store" });
  });
  it("keeps loaded records after a failed next page and retries the same bounded cursor", async () => {
    const mock = vi.fn().mockResolvedValueOnce(json({ items: [asset], next_cursor: cursor })).mockResolvedValueOnce(json({}, 503)).mockResolvedValueOnce(json({ items: [{ ...asset, id: org, title: "Next media" }], next_cursor: null })); vi.stubGlobal("fetch", mock);
    await act(async () => { render(<MediaMetadata org={org} locale="en" />); });
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Load more" })); });
    expect(screen.getByText("Synthetic media")).toBeTruthy();
    expect(screen.getByRole("status").textContent).toContain("could not be loaded");
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Load more" })); });
    expect(screen.getByText("Next media")).toBeTruthy();
    expect(mock.mock.calls[1][0]).toBe(`/api/cms/organizations/${org}/assets?cursor=${cursor}`);
    expect(mock.mock.calls[2][0]).toBe(mock.mock.calls[1][0]);
    expect(mock.mock.calls.every(call => !call[1]?.method || call[1].method === "GET")).toBe(true);
  });
});
