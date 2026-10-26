import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import CardEditor from "./card";
import CatalogueEditor from "./catalogue";
import QuotesEditor from "./quotes";
import { Contacts, Tasks } from "./crm";
import { type Card, type Contact, type Quote, localInput } from "./client";
const base = "/api/business-tools/organizations/11111111-1111-4111-8111-111111111111/profiles/22222222-2222-4222-8222-222222222222";
const id = "33333333-3333-4333-8333-333333333333";
const card: Card = { name_en: "Synthetic business", name_ta: "செயற்கை தொழில்", tagline_en: "", tagline_ta: "", description_en: "Original", description_ta: "", phone: "", email: "", website: "", address_en: "", address_ta: "", version: 1, published: false, share_id: id };
const contact: Contact = { id, version: 1, name: "Synthetic customer", email: "", phone: "", notes: "", status: "lead" };
const quote: Quote = { id, version: 1, status: "draft", customer_name: "Synthetic customer", customer_address: "", issued_on: "2026-10-24", valid_until: null, notes: "", currency: "INR", discount: "0.00", lines: [{ description: "Consulting", quantity: "1.005", unit_price: "0.10", catalogue_item_id: null, catalogue_version: null, line_total: "0.10" }], subtotal: "0.10", total: "0.10", issued_at: null };
const page = <T,>(items: T[]) => ({ items, limit: 25, offset: 0 });
function mockTransport(handler: (url: string, options?: RequestInit) => Promise<Response> | Response) {
  const fetchMock = vi.fn(async (url: string, options?: RequestInit) => url === "/api/session/csrf" ? Response.json({ csrf_token: "csrf" }) : handler(url, options));
  vi.stubGlobal("fetch", fetchMock); return fetchMock;
}
afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });
describe("entrepreneur tool workflows", () => {
  it("defaults a date-only quotation to the owner's local day across UTC midnight", () => {
    vi.useFakeTimers(); vi.setSystemTime(new Date("2026-10-23T19:30:00Z"));
    vi.spyOn(Date.prototype, "getTimezoneOffset").mockReturnValue(-330);
    render(<QuotesEditor base={base} locale="en" initial={page([])} items={[]} />);
    expect((screen.getByLabelText("Quotation date") as HTMLInputElement).value).toBe("2026-10-24");
  });
  it("keeps interrupted card input and retries the exact command UUID/body before further editing", async () => {
    const writes: string[] = [];
    mockTransport((_url, options) => { writes.push(String(options?.body)); if (writes.length === 1) throw new TypeError("lost response"); return Response.json({ ...card, name_en: "Preserved edit", version: 2 }); });
    render(<CardEditor base={base} locale="en" initial={card} />);
    fireEvent.change(screen.getByLabelText("Name in English"), { target: { value: "Preserved edit" } });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await screen.findByText(/The response was interrupted/);
    expect((screen.getByLabelText("Name in English") as HTMLInputElement).value).toBe("Preserved edit");
    expect((screen.getByRole("button", { name: "Save draft" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Confirm interrupted request" }));
    await screen.findByText("Saved."); expect(writes).toHaveLength(2); expect(writes[0]).toBe(writes[1]);
    expect(JSON.parse(writes[0]).request_id).toMatch(/^[0-9a-f-]{36}$/);
  });
  it("requires authoritative stale-card review and preserves the user's edit during reload", async () => {
    const writes: Record<string, unknown>[] = [];
    mockTransport((_url, options) => { if (options?.method !== "POST") return Response.json({ ...card, name_en: "Other session", version: 3 }); writes.push(JSON.parse(String(options.body))); return new Response("{}", { status: 409 }); });
    render(<CardEditor base={base} locale="en" initial={card} />);
    fireEvent.change(screen.getByLabelText("Name in English"), { target: { value: "My edit" } }); fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await screen.findByText(/A newer version exists/); fireEvent.click(screen.getByRole("button", { name: "Load latest saved version" }));
    await screen.findByText(/Other session/); expect((screen.getByLabelText("Name in English") as HTMLInputElement).value).toBe("My edit");
    fireEvent.click(screen.getByRole("button", { name: /I reviewed the latest version/ })); fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(writes).toHaveLength(2)); expect(writes[1].expected_version).toBe(3); expect(writes[1].name_en).toBe("My edit");
  });
  it("publishes only saved card details and provides an explicit revocation command", async () => {
    const writes: Record<string, unknown>[] = [];
    mockTransport((_url, options) => { const body = JSON.parse(String(options?.body)); writes.push(body); return Response.json({ ...card, published: body.published, version: writes.length + 1 }); });
    render(<CardEditor base={base} locale="en" initial={card} />);
    fireEvent.click(screen.getByRole("button", { name: "Publish these saved details" })); await screen.findByRole("link", { name: "Open shared page" });
    fireEvent.click(screen.getByRole("button", { name: "Revoke sharing" })); await waitFor(() => expect(screen.queryByRole("link", { name: "Open shared page" })).toBeNull());
    expect(writes.map(x => x.published)).toEqual([true, false]);
  });
  it("submits catalogue money as decimal text and bilingual explicit fields", async () => {
    let body: Record<string, unknown> = {};
    mockTransport((_url, options) => { if (options?.method !== "POST") return Response.json({ settings: null, ...page([]) }); body = JSON.parse(String(options.body)); return Response.json({ ...body, id, version: 1 }); });
    render(<CatalogueEditor base={base} locale="ta" initial={{ settings: null, ...page([]) }} onItems={() => undefined} />);
    fireEvent.change(screen.getByLabelText("ஆங்கிலப் பெயர்"), { target: { value: "Product" } });
    fireEvent.change(screen.getByLabelText("தமிழ்ப் பெயர்"), { target: { value: "பொருள்" } });
    fireEvent.change(screen.getByLabelText("அலகு விலை (விருப்பம்)"), { target: { value: "0.10" } });
    fireEvent.click(screen.getByRole("button", { name: "பொருளைச் சேர்" }));
    await screen.findByText("சேமிக்கப்பட்டது."); expect(body.price).toBe("0.10"); expect(body.name_ta).toBe("பொருள்");
  });
  it("reviews authoritative decimal totals before issuing and locks the issued version", async () => {
    let body: Record<string, unknown> = {};
    mockTransport((_url, options) => { body = JSON.parse(String(options?.body)); return Response.json({ ...quote, version: 2, status: "issued", issued_at: "2026-10-24T00:00:00Z" }); });
    render(<QuotesEditor base={base} locale="en" initial={page([quote])} items={[]} />);
    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    expect((screen.getByRole("button", { name: "Issue saved quotation" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByLabelText(/I reviewed the saved quotation/)); fireEvent.click(screen.getByRole("button", { name: "Issue saved quotation" }));
    await screen.findByRole("link", { name: "Download printable copy" }); expect(body.expected_version).toBe(1);
    expect(screen.getByLabelText("Customer name").matches(":disabled")).toBe(true);
    expect(screen.queryByRole("button", { name: "Issue saved quotation" })).toBeNull();
  });
  it("saves draft quotation precision without browser arithmetic", async () => {
    let body: Record<string, unknown> = {};
    mockTransport((_url, options) => { body = JSON.parse(String(options?.body)); return Response.json(quote); });
    render(<QuotesEditor base={base} locale="en" initial={page([quote])} items={[]} />); fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    fireEvent.change(screen.getByLabelText("Quantity"), { target: { value: "1.015" } }); fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await screen.findByText("Saved."); expect((body.lines as { quantity: string; unit_price: string }[])[0]).toMatchObject({ quantity: "1.015", unit_price: "0.10" });
    expect(body).not.toHaveProperty("total");
  });

  it("refreshes stale catalogue references explicitly and clears them when currency changes", async () => {
    let body: Record<string, unknown> = {};
    mockTransport((_url, options) => { body = JSON.parse(String(options?.body)); return Response.json({ ...quote, lines: [{ ...quote.lines[0], catalogue_item_id: id, catalogue_version: 2, unit_price: "20.00" }] }); });
    const referenced = { ...quote, lines: [{ ...quote.lines[0], catalogue_item_id: id, catalogue_version: 1 }] };
    render(<QuotesEditor base={base} locale="en" initial={page([referenced])} items={[{ id, version: 2, kind: "service", name_en: "Current catalogue service", name_ta: "சேவை", description_en: "", description_ta: "", available: true, price: "20.00", currency: "INR" }]} />);
    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    fireEvent.click(screen.getByRole("button", { name: "Use current catalogue values" }));
    expect((screen.getByLabelText("Unit price") as HTMLInputElement).value).toBe("20.00");
    fireEvent.click(screen.getByRole("button", { name: "Save draft" })); await screen.findByText("Saved.");
    expect((body.lines as { catalogue_version: number }[])[0].catalogue_version).toBe(2);
    fireEvent.click(screen.getByRole("button", { name: "Use saved details" }));
    fireEvent.change(screen.getByLabelText("Currency"), { target: { value: "USD" } });
    expect((screen.getByLabelText("Unit price") as HTMLInputElement).readOnly).toBe(false);
    expect((screen.getByLabelText("Unit price") as HTMLInputElement).value).toBe("0.00");
  });
  it("stores a follow-up in UTC and keeps contact details private", async () => {
    let body: Record<string, unknown> = {};
    mockTransport((_url, options) => { if (options?.method !== "POST") return Response.json(page([])); body = JSON.parse(String(options.body)); return Response.json({ ...body, id, version: 1, status: "pending" }); });
    const view = render(<Tasks base={base} locale="en" initial={page([])} contacts={[contact]} />);
    fireEvent.change(screen.getByLabelText("Contact name"), { target: { value: id } });
    fireEvent.change(screen.getByLabelText("Follow-up title"), { target: { value: "Discuss order" } });
    fireEvent.change(screen.getByLabelText("Due at (your local time)"), { target: { value: "2026-11-01T09:30" } });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" })); await screen.findByText("Saved.");
    expect(body.due_at).toBe(new Date("2026-11-01T09:30").toISOString()); expect(localInput(String(body.due_at))).toBe("2026-11-01T09:30");
    expect(body.contact_id).toBe(id); expect(within(view.container).queryByRole("link")).toBeNull();
  });
  it("keeps archived contacts and completed follow-ups immutable in the editor", () => {
    const view = render(<Contacts base={base} locale="en" initial={page([{ ...contact, status: "archived" }])} onContacts={() => undefined} />);
    fireEvent.click(screen.getByRole("button", { name: "Edit" })); expect(screen.getByLabelText("Contact name").matches(":disabled")).toBe(true);
    view.unmount(); render(<Tasks base={base} locale="en" initial={page([{ id, contact_id: id, version: 1, title: "Done", notes: "", due_at: "2026-10-24T00:00:00Z", status: "completed" }])} contacts={[contact]} />);
    fireEvent.click(screen.getByRole("button", { name: "Edit" })); expect(screen.getByLabelText("Follow-up title").matches(":disabled")).toBe(true);
  });

  it("recovers a task settled by another session even when it disappears from the filtered page", async () => {
    const task = { id, contact_id: id, version: 1, title: "Original", notes: "", due_at: "2026-10-24T00:00:00Z", status: "pending" as const };
    mockTransport((url, options) => options?.method === "POST" ? new Response("{}", { status: 409 }) : Response.json(url.endsWith(`/tasks/${id}`) ? { ...task, version: 2, status: "completed" } : page([])));
    render(<Tasks base={base} locale="en" initial={page([task])} contacts={[contact]} />);
    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    fireEvent.change(screen.getByLabelText("Follow-up title"), { target: { value: "Kept local edit" } });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" })); await screen.findByText(/A newer version exists/);
    fireEvent.click(screen.getByRole("button", { name: "Load latest saved version" })); await screen.findByText(/Original · v2/);
    expect((screen.getByLabelText("Follow-up title") as HTMLInputElement).value).toBe("Kept local edit");
    fireEvent.click(screen.getByRole("button", { name: /I reviewed the latest version/ }));
    expect(screen.getByLabelText("Follow-up title").matches(":disabled")).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Use saved details" }));
    expect((screen.getByLabelText("Follow-up title") as HTMLInputElement).value).toBe("Original");
    expect((screen.getByRole("button", { name: "New follow-up" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("can discard preserved edits after a concurrent contact archive", async () => {
    mockTransport((url, options) => options?.method === "POST" ? new Response("{}", { status: 409 }) : Response.json(url.endsWith(`/contacts/${id}`) ? { ...contact, version: 2, status: "archived" } : page([])));
    render(<Contacts base={base} locale="en" initial={page([contact])} onContacts={() => undefined} />);
    fireEvent.click(screen.getByRole("button", { name: "Edit" })); fireEvent.change(screen.getByLabelText("Contact name"), { target: { value: "Local change" } });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" })); await screen.findByText(/A newer version exists/);
    fireEvent.click(screen.getByRole("button", { name: "Load latest saved version" })); await screen.findByText(/Synthetic customer · v2/);
    fireEvent.click(screen.getByRole("button", { name: "Use saved details" }));
    expect((screen.getByLabelText("Contact name") as HTMLInputElement).value).toBe("Synthetic customer");
    expect((screen.getByRole("button", { name: "New contact" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("applies bounded contact search and combines owner task filters", async () => {
    const fetchMock = mockTransport(() => Response.json(page([])));
    const view = render(<Contacts base={base} locale="en" initial={page([])} onContacts={() => undefined} />);
    fireEvent.change(screen.getByLabelText("Search contacts by name"), { target: { value: "Synthetic & customer" } });
    fireEvent.change(screen.getByLabelText("Filter by status"), { target: { value: "customer" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply filters" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const contactsUrl = new URL(fetchMock.mock.calls[0][0], "http://localhost");
    expect(contactsUrl.searchParams.get("search")).toBe("Synthetic & customer"); expect(contactsUrl.searchParams.get("status")).toBe("customer");
    view.unmount(); fetchMock.mockClear();
    render(<Tasks base={base} locale="en" initial={page([])} contacts={[contact]} />);
    fireEvent.change(screen.getByLabelText("Filter by contact"), { target: { value: id } });
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    fireEvent.change(screen.getByLabelText("Filter by status"), { target: { value: "pending" } });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const taskUrl = new URL(fetchMock.mock.calls[1][0], "http://localhost"); expect(taskUrl.searchParams.get("status")).toBe("pending"); expect(taskUrl.searchParams.get("contact_id")).toBe(id);
  });
});
