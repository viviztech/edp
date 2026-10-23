import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import EnquiryInbox from "./view";
import { enquiryWords, type Enquiry } from "../../../../lib/enquiry-content";
const org = "11111111-1111-4111-8111-111111111111", id = "22222222-2222-4222-8222-222222222222", other = "33333333-3333-4333-8333-333333333333";
const first: Enquiry = { id, name: "Synthetic Enquirer", email: "enquirer@example.test", phone: "", message: "Question about the programme", consent_version: "synthetic-v1", status: "new", version: 1, created_at: "2026-10-23T06:00:00Z", updated_at: "2026-10-23T06:00:00Z" };
const response = (value: object, status = 200) => Promise.resolve(new Response(JSON.stringify(value), { status }));
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
function mockApi(options: { conflict?: boolean; interrupted?: boolean; page?: boolean } = {}) {
  let item = first; const writes: Record<string, unknown>[] = []; const reads: string[] = [];
  vi.stubGlobal("fetch", vi.fn((input: string, init?: RequestInit) => {
    if (input === "/api/session/csrf") return response({ csrf_token: "csrf" });
    if (init?.method === "POST") {
      expect(new Headers(init.headers).get("x-csrf-token")).toBe("csrf"); const body = JSON.parse(String(init.body)); writes.push(body);
      if (options.conflict && writes.length === 1) { item = { ...item, status: "reviewed", version: 2 }; return response({}, 409); }
      if (options.interrupted && writes.length === 1) { item = { ...item, status: "reviewed", version: 2 }; return Promise.reject(new Error("response lost")); }
      item = { ...item, status: body.status, version: item.version + 1 }; return response(item);
    }
    reads.push(input);
    if (input.includes("/queue")) return response({ items: input.includes("cursor=") ? [{ ...first, id: other, name: "Second enquirer" }] : [item], next_cursor: options.page && !input.includes("cursor=") ? id : null });
    return response(item);
  }));
  return { writes, reads };
}
async function open() { fireEvent.click(await screen.findByRole("button", { name: /Synthetic Enquirer/ })); return screen.findByRole("region", { name: "Enquiry details" }); }
describe("staff enquiry workflow", () => {
  it("shows scoped details while hiding mutation controls for a viewer", async () => {
    const api = mockApi(); render(<EnquiryInbox org={org} locale="en" permissions={["enquiry.view"]} />);
    const details = await open(); await within(details).findByText(first.email);
    expect(within(details).queryByRole("button", { name: "Mark reviewed" })).toBeNull(); expect(api.writes).toHaveLength(0);
    expect(within(details).queryByText("Internal note")).toBeNull();
  });
  it("uses the current expected version for each forward lifecycle command", async () => {
    const api = mockApi(); render(<EnquiryInbox org={org} locale="en" permissions={["enquiry.view", "enquiry.manage"]} />);
    const details = await open(); fireEvent.click(await within(details).findByRole("button", { name: "Mark reviewed" }));
    fireEvent.click(await within(details).findByRole("button", { name: "Close enquiry" }));
    await waitFor(() => expect(api.writes).toEqual([{ expected_version: 1, status: "reviewed" }, { expected_version: 2, status: "closed" }]));
    await waitFor(() => expect(within(details).queryByRole("button", { name: "Close enquiry" })).toBeNull());
  });
  it.each([{ conflict: true, text: enquiryWords.en.conflict }, { interrupted: true, text: enquiryWords.en.uncertain }])("locks uncertain/stale commands until details are explicitly refreshed", async options => {
    const api = mockApi(options); render(<EnquiryInbox org={org} locale="en" permissions={["enquiry.view", "enquiry.manage"]} />);
    const details = await open(); fireEvent.click(await within(details).findByRole("button", { name: "Mark reviewed" })); await screen.findByText(options.text);
    expect((within(details).getByRole("button", { name: "Mark reviewed" }) as HTMLButtonElement).disabled).toBe(true); expect(api.writes).toHaveLength(1);
    fireEvent.click(within(details).getByRole("button", { name: "Refresh" })); await screen.findByText(enquiryWords.en.refreshed);
    expect(screen.queryByRole("button", { name: /Synthetic Enquirer/ })).toBeNull();
    expect(api.writes).toHaveLength(1); fireEvent.click(within(details).getByRole("button", { name: "Close enquiry" }));
    await waitFor(() => expect(api.writes[1]).toEqual({ expected_version: 2, status: "closed" }));
  });
  it("loads later queue pages and preserves the chosen status filter", async () => {
    const api = mockApi({ page: true }); render(<EnquiryInbox org={org} locale="en" permissions={["enquiry.view"]} />);
    fireEvent.click(await screen.findByRole("button", { name: "Load more" })); await screen.findByRole("button", { name: /Second enquirer/ });
    expect(api.reads).toContain(`/api/enquiries/organizations/${org}/enquiries/queue?limit=25&status=new&cursor=${id}`);
    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "closed" } });
    await waitFor(() => expect(api.reads).toContain(`/api/enquiries/organizations/${org}/enquiries/queue?limit=25&status=closed`));
  });
  it("renders Tamil queue/status controls", async () => {
    mockApi(); render(<EnquiryInbox org={org} locale="ta" permissions={["enquiry.view"]} />);
    expect(screen.getByLabelText(enquiryWords.ta.status)).toBeTruthy(); await screen.findByRole("button", { name: /Synthetic Enquirer/ });
  });
});
