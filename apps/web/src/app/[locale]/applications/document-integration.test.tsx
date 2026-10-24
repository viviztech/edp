import { webcrypto } from "node:crypto";
import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import ApplicationWorkspace from "./view";
import { document, documentApplication, documentList, documentOrg, requirement } from "../../../test-fixtures/application-documents";

const form = { id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", organization_id: documentOrg, version: 1, title_en: "Synthetic form", title_ta: "செயற்கைப் படிவம்", collection_enabled: true, max_upload_bytes: 1024, document_requirements: [requirement], fields: [{ id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", key: "proposal", section: "general", label_en: "Proposal", label_ta: "திட்டம்", field_type: "text", required: true, position: 1 }], acknowledgements: [{ id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc", key: "declaration", kind: "declaration", label_en: "Synthetic declaration", label_ta: "செயற்கை அறிவிப்பு", required: true, position: 1 }, { id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd", key: "consent", kind: "consent", label_en: "Synthetic consent", label_ta: "செயற்கை ஒப்புதல்", required: true, position: 2 }] };
const cycle = { id: "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee", code: "SYNTHETIC", name_en: "Synthetic intake", name_ta: "செயற்கைச் சேர்க்கை", form_id: form.id, opens_at: "2026-10-01T00:00:00Z", closes_at: "2026-11-01T00:00:00Z" };
const draft = { id: documentApplication, cycle_id: cycle.id, form, state: "draft", version: 1, revision: 1, completion_percent: 0, answers: [], updated_at: "2026-10-23T08:00:00Z" };
const root = `/api/applications/organizations/${documentOrg}`;
const reply = (value: unknown, status = 200) => Promise.resolve(Response.json(value, { status }));
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("application answer and document version integration", () => {
  it("saves dirty answers before document mutation and submits using the acknowledged document version", async () => {
    vi.stubGlobal("crypto", webcrypto); vi.spyOn(window, "confirm").mockReturnValue(true);
    let version = 1, uploaded = false;
    let answers: { field_id: string; value: string }[] = [];
    const writes: { path: string; body: Record<string, unknown> }[] = [];
    vi.stubGlobal("fetch", vi.fn((input: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      if (input === "/api/session/csrf") return reply({ csrf_token: "csrf" });
      if (input.includes("/mine")) return reply({ items: [], next_cursor: null });
      if (input === root + "/cycles") return reply({ items: [cycle] });
      if (input === `${root}/cycles/${cycle.id}/application`) return reply({ ...draft, version, answers });
      if (method === "GET" && input.includes("/documents")) return reply(documentList(uploaded ? [{ ...document, usable: true, file: { ...document.file, state: "clean", version: 5 } }] : [], { application_version: version }));
      if (method === "PUT") { uploaded = true; return reply({ application_version: version, document: { ...document, file: { ...document.file, state: "quarantined", version: 3 } } }); }
      const body = JSON.parse(String(init?.body)); writes.push({ path: input, body });
      if (method === "PATCH") { expect(body.expected_version).toBe(version); version++; answers = body.answers; return reply({ ...draft, version, answers, completion_percent: 100 }); }
      if (input.endsWith("/documents")) { expect(body.expected_version).toBe(version); version++; return reply({ application_version: version, document }, 201); }
      if (input.endsWith("/submit")) { expect(body.expected_version).toBe(version); return reply({ ...draft, version: ++version, state: "submitted", answers, application_number: "SYNTHETIC-RECEIPT", submitted_at: "2026-10-23T09:00:00Z", accepted_acknowledgements: form.acknowledgements.map(item => ({ definition_id: item.id, accepted_at: "2026-10-23T09:00:00Z" })), status_history: [] }); }
      return reply({}, 404);
    }));
    render(<ApplicationWorkspace org={documentOrg} locale="en" />);
    const proposal = await screen.findByRole("textbox", { name: "Proposal *" });
    fireEvent.change(proposal, { target: { value: "Keep this business proposal" } });
    await waitFor(() => expect(screen.getByRole("button", { name: "Upload document" }).matches(":disabled")).toBe(true));
    expect(screen.getByRole("button", { name: "Submit application" }).matches(":disabled")).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Upload document" }).matches(":disabled")).toBe(false));
    fireEvent.click(screen.getByRole("button", { name: "Upload document" }));
    const file = new File(["abc"], "synthetic.pdf", { type: "application/pdf" });
    Object.defineProperty(file, "arrayBuffer", { value: () => Promise.resolve(new TextEncoder().encode("abc").buffer) });
    fireEvent.change(screen.getByLabelText("Choose a file"), { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: "Upload selected file" }));
    await screen.findByText("Awaiting scan");
    expect((screen.getByRole("textbox", { name: "Proposal *" }) as HTMLInputElement).value).toBe("Keep this business proposal");
    fireEvent.click(screen.getByRole("button", { name: "Refresh document status" }));
    await screen.findByText("Verified clean");
    for (const label of ["Synthetic declaration", "Synthetic consent"]) fireEvent.click(screen.getByLabelText(new RegExp(label)));
    fireEvent.click(screen.getByRole("button", { name: "Submit application" }));
    await screen.findByText(/SYNTHETIC-RECEIPT/);
    expect(writes.find(call => call.path.endsWith("/documents"))?.body.expected_version).toBe(2);
    expect(writes.filter(call => call.path.includes("/draft/") && !call.path.endsWith("/submit")).at(-1)?.body.expected_version).toBe(3);
    expect(writes.find(call => call.path.endsWith("/submit"))?.body.expected_version).toBe(4);
  });

  it("preserves dirty answers when a metadata read reveals a newer application and requires explicit discard", async () => {
    let resolveDocuments!: (value: Response) => void;
    const pendingRead = new Promise<Response>(resolve => { resolveDocuments = resolve; });
    let reads = 0, documentReads = 0;
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    vi.stubGlobal("fetch", vi.fn((input: string) => {
      if (input.includes("/mine")) return reply({ items: [], next_cursor: null });
      if (input === root + "/cycles") return reply({ items: [cycle] });
      if (input === `${root}/cycles/${cycle.id}/application`) return reply(++reads === 1 ? draft : { ...draft, version: 2, answers: [{ field_id: form.fields[0].id, value: "Remote saved proposal" }] });
      if (input.includes("/documents")) return ++documentReads === 1 ? pendingRead : reply(documentList([], { application_version: 2 }));
      return reply({}, 404);
    }));
    render(<ApplicationWorkspace org={documentOrg} locale="en" />);
    fireEvent.change(await screen.findByRole("textbox", { name: "Proposal *" }), { target: { value: "Retained local proposal" } });
    await act(async () => { resolveDocuments(Response.json(documentList([], { application_version: 2 }))); });
    await screen.findByText("The application version changed. Reload and review the saved application before changing documents.");
    const input = screen.getByRole("textbox", { name: "Proposal *" });
    expect((input as HTMLInputElement).value).toBe("Retained local proposal"); expect(input.matches(":disabled")).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Reload application" }));
    expect(reads).toBe(1); expect(confirm).toHaveBeenCalled();
    confirm.mockReturnValue(true); fireEvent.click(screen.getByRole("button", { name: "Reload application" }));
    await waitFor(() => expect((screen.getByRole("textbox", { name: "Proposal *" }) as HTMLInputElement).value).toBe("Remote saved proposal"));
    await waitFor(() => expect(within(screen.getByRole("region", { name: "Application documents" })).getByRole("button", { name: "Upload document" }).matches(":disabled")).toBe(false));
  });
});
