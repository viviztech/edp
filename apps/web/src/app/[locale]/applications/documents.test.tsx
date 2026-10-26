import { webcrypto } from "node:crypto";
import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import ApplicationDocuments from "./documents";
import { document, documentApplication, documentList, documentOrg, requirement } from "../../../test-fixtures/application-documents";
import type { components } from "../../../lib/api-contracts";

const root = `/api/applications/organizations/${documentOrg}/applications/${documentApplication}/documents`;
const reply = (value: unknown, status = 200) => Promise.resolve(Response.json(value, { status }));
const clean = { ...document, usable: true, file: { ...document.file, state: "clean" as const, version: 5 } };
afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });
function setup(extra: Partial<React.ComponentProps<typeof ApplicationDocuments>> = {}) {
  const callbacks = { onBusy: vi.fn(), onVersion: vi.fn(), onReadiness: vi.fn(), onPendingChange: vi.fn() };
  render(<ApplicationDocuments org={documentOrg} applicationId={documentApplication} applicationVersion={1} requirements={[requirement]} collectionEnabled maxUploadBytes={1024} locale="en" readOnly={false} blocked={false} dirty={false} {...callbacks} {...extra} />);
  return callbacks;
}
async function choose(size = 3) {
  fireEvent.click(await screen.findByRole("button", { name: "Upload document" }));
  const file = new File([new Uint8Array(size).fill(97)], "sensitive-name.pdf", { type: "application/pdf" });
  Object.defineProperty(file, "arrayBuffer", { value: () => Promise.resolve(new TextEncoder().encode("abc").buffer) });
  fireEvent.change(screen.getByLabelText("Choose a file"), { target: { files: [file] } });
  return file;
}

describe("owned application documents", () => {
  it("explains disabled collection and the operational limit without collecting bytes", async () => {
    const fetchMock = vi.fn().mockImplementation(() => reply(documentList([], { collection_enabled: false, max_upload_bytes: 512 })));
    vi.stubGlobal("fetch", fetchMock); setup({ collectionEnabled: false });
    expect(await screen.findByText("File collection is disabled. These configured requirements do not provide upload access.")).toBeTruthy();
    await waitFor(() => expect(screen.getByText("512")).toBeTruthy());
    expect(screen.queryByRole("button", { name: "Upload document" })).toBeNull();
    expect(screen.getByRole("region", { name: "Application documents" }).querySelector("input[type=file]")).toBeNull();
    expect(fetchMock.mock.calls).toHaveLength(1);
  });

  it("rejects a file above the server operational limit before metadata creation", async () => {
    vi.stubGlobal("crypto", webcrypto);
    const fetchMock = vi.fn().mockImplementation(() => reply(documentList([], { max_upload_bytes: 2 })));
    vi.stubGlobal("fetch", fetchMock); setup();
    await waitFor(() => expect(screen.getByRole("button", { name: "Upload document" }).matches(":disabled")).toBe(false));
    await choose(); fireEvent.click(screen.getByRole("button", { name: "Upload selected file" }));
    expect(await screen.findByText("Choose a nonempty file in an allowed format and within the displayed size limit.")).toBeTruthy();
    expect(fetchMock.mock.calls).toHaveLength(1);
  });

  it("registers a digest, uploads raw bytes once and polls only reads until the exact file is clean", async () => {
    vi.stubGlobal("crypto", webcrypto);
    let registered = false, uploaded = false;
    const writes: { method: string; body: unknown; headers?: HeadersInit }[] = [];
    const fetchMock = vi.fn((input: string, init?: RequestInit) => {
      if (input === "/api/session/csrf") return reply({ csrf_token: "csrf" });
      const method = init?.method ?? "GET";
      if (method === "POST") { registered = true; writes.push({ method, body: JSON.parse(String(init?.body)) }); return reply({ application_version: 2, document }, 201); }
      if (method === "PUT") { uploaded = true; writes.push({ method, body: init?.body, headers: init?.headers }); return reply({ application_version: 2, document: { ...document, file: { ...document.file, state: "quarantined", version: 3 } } }); }
      return reply(documentList(uploaded ? [clean] : registered ? [document] : [], { application_version: registered ? 2 : 1 }));
    });
    vi.stubGlobal("fetch", fetchMock); const callbacks = setup();
    await waitFor(() => expect(screen.getByRole("button", { name: "Upload document" }).matches(":disabled")).toBe(false));
    const file = await choose(); fireEvent.click(screen.getByRole("button", { name: "Upload selected file" }));
    await screen.findByText("Awaiting scan");
    expect(writes).toHaveLength(2);
    expect(writes[0].body).toMatchObject({ expected_version: 1, requirement_id: requirement.id, byte_size: 3, sha256: document.file.sha256 });
    expect(writes[0].body).not.toHaveProperty("name"); expect(writes[1].body).toBe(file);
    expect(writes[1].headers).toMatchObject({ "If-Match": '"1"', "Content-Type": "application/pdf", "x-csrf-token": "csrf" });
    expect(await screen.findByText("Verified clean", {}, { timeout: 5000 })).toBeTruthy();
    // Readiness is reported by an effect after the clean state is rendered.
    await waitFor(() => expect(callbacks.onReadiness).toHaveBeenLastCalledWith(true));
    expect(writes).toHaveLength(2);
  }, 10000);

  it("freezes an uncertain registration and recovers the same UUID before any byte continuation", async () => {
    vi.stubGlobal("crypto", webcrypto); let calls = 0, puts = 0;
    const bodies: components["schemas"]["DocumentCreate"][] = [];
    vi.stubGlobal("fetch", vi.fn((input: string, init?: RequestInit) => {
      if (input === "/api/session/csrf") return reply({ csrf_token: "csrf" });
      if (init?.method === "POST") { bodies.push(JSON.parse(String(init.body))); if (++calls === 1) return Promise.reject(new Error("lost after registration")); return reply({ application_version: 2, document }, 201); }
      if (init?.method === "PUT") { puts++; return reply({ application_version: 2, document: clean }); }
      return reply(documentList());
    }));
    setup(); await waitFor(() => expect(screen.getByRole("button", { name: "Upload document" }).matches(":disabled")).toBe(false));
    await choose(); fireEvent.click(screen.getByRole("button", { name: "Upload selected file" }));
    await screen.findByRole("button", { name: "Recover the same document registration" });
    expect(puts).toBe(0); expect(screen.queryByLabelText("Choose a file")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Recover the same document registration" }));
    await screen.findByRole("button", { name: "Continue this registered upload" });
    expect(bodies).toHaveLength(2); expect(bodies[0]).toEqual(bodies[1]); expect(puts).toBe(0);
    fireEvent.click(screen.getByRole("button", { name: "Continue this registered upload" }));
    await screen.findByText("Verified clean"); expect(puts).toBe(1);
  });

  it("reconciles a lost upload response by reading the binding without resending bytes", async () => {
    vi.stubGlobal("crypto", webcrypto); let puts = 0;
    let finishRead!: (response: Response) => void;
    const savedDocument = new Promise<Response>(resolve => { finishRead = resolve; });
    const fetchMock = vi.fn((input: string, init?: RequestInit) => {
      if (input === "/api/session/csrf") return reply({ csrf_token: "csrf" });
      if (init?.method === "POST") return reply({ application_version: 2, document }, 201);
      if (init?.method === "PUT") { puts++; return Promise.reject(new Error("lost after upload")); }
      if (input === root + "/" + document.id) return savedDocument;
      return reply(documentList());
    });
    vi.stubGlobal("fetch", fetchMock);
    const callbacks = setup(); await waitFor(() => expect(screen.getByRole("button", { name: "Upload document" }).matches(":disabled")).toBe(false));
    await choose(); fireEvent.click(screen.getByRole("button", { name: "Upload selected file" }));
    const readCurrent = await screen.findByRole("button", { name: "Read current document" });
    await waitFor(() => expect(readCurrent.matches(":disabled")).toBe(false));
    fireEvent.click(readCurrent);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(root + "/" + document.id, expect.objectContaining({ method: "GET" })));
    expect(callbacks.onReadiness).toHaveBeenLastCalledWith(false);
    expect(screen.queryByText("Verified clean")).toBeNull();
    await act(async () => { finishRead(Response.json({ application_version: 2, document: clean })); });
    await screen.findByText("Verified clean"); expect(puts).toBe(1);
    await waitFor(() => expect(callbacks.onReadiness).toHaveBeenLastCalledWith(true));
    expect(screen.queryByLabelText("Choose a file")).toBeNull();
  });

  it("preserves scalar edits and renders failed or disposed files as unusable evidence", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => reply(documentList([{ ...document, file: { ...document.file, state: "infected" } }]))));
    const callbacks = setup({ dirty: true });
    await screen.findByText("Unsafe file");
    expect(screen.getByText("Save your application answers before changing documents. Your entered answers are preserved.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Replace document" }).matches(":disabled")).toBe(true);
    expect(screen.queryByRole("link", { name: "Download verified document" })).toBeNull();
    expect(callbacks.onReadiness).toHaveBeenLastCalledWith(false);
  });

  it("uses immutable submitted evidence versions and Tamil labels without upload controls", async () => {
    const evidence = { file_id: clean.file.id, file_version: 5, byte_size: 3, sha256: clean.file.sha256, frozen_at: "2026-10-23T09:00:00Z" };
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => reply(documentList([{ ...clean, file: { ...clean.file, version: 7 }, submitted_evidence: evidence }]))));
    setup({ locale: "ta", readOnly: true });
    await screen.findByText("சரிபார்க்கப்பட்ட பாதுகாப்பான கோப்பு");
    expect(screen.getByRole("heading", { name: "செயற்கைச் சான்று" })).toBeTruthy();
    expect(screen.getByText(/கோப்புப் பதிப்பு: 5/)).toBeTruthy();
    expect(within(screen.getByRole("region", { name: "விண்ணப்ப ஆவணங்கள்" })).queryByRole("button", { name: "ஆவணத்தைப் பதிவேற்று" })).toBeNull();
  });
  it("does not count an expired clean scan as usable evidence or offer its bytes", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => reply(documentList([{ ...clean, usable: false }]))));
    const callbacks = setup();
    await screen.findByText("Verified clean");
    expect(screen.getByText("This evidence is unavailable under the current retention or file rules.")).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Download verified document" })).toBeNull();
    expect(callbacks.onReadiness).toHaveBeenLastCalledWith(false);
  });
});
