import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import ApplicationDefinitionWorkspace from "./view";
import { documentOrg, requirement } from "../../../../test-fixtures/application-documents";
import type { components } from "../../../../lib/api-contracts";

const id = "99999999-9999-4999-8999-999999999999";
const original: components["schemas"]["DefinitionView"] = { id, organization_id: documentOrg, version: 1, title_en: "Synthetic application", title_ta: "செயற்கை விண்ணப்பம்", state: "draft", revision: 1, published_at: null, created_at: "2026-10-23T08:00:00Z", document_requirements: [requirement], collection_enabled: false, max_upload_bytes: 1024, fields: [{ id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", key: "proposal", section: "general", label_en: "Proposal", label_ta: "திட்டம்", field_type: "text", required: true, position: 1 }], acknowledgements: [{ id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", key: "declaration", kind: "declaration", label_en: "Synthetic declaration", label_ta: "செயற்கை அறிவிப்பு", required: true, position: 1 }, { id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc", key: "consent", kind: "consent", label_en: "Synthetic consent", label_ta: "செயற்கை ஒப்புதல்", required: true, position: 2 }] };
const permissions = ["application.form.view", "application.form.create", "application.form.update", "application.form.publish", "files.policy.view"];
const root = `/api/application-definitions/organizations/${documentOrg}/definitions`;
const reply = (value: unknown, status = 200) => Promise.resolve(Response.json(value, { status }));
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("application definition requirements and recovery", () => {
  it("preserves bilingual requirements through a conflict and requires saved-revision review", async () => {
    let current = structuredClone(original), conflict = true;
    const bodies: Record<string, unknown>[] = [];
    vi.stubGlobal("fetch", vi.fn((input: string, init?: RequestInit) => {
      if (input === "/api/session/csrf") return reply({ csrf_token: "csrf" });
      if (input.startsWith("/api/file-policies")) return reply({ items: [], next_cursor: null });
      if (init?.method === "PATCH") {
        const body = JSON.parse(String(init.body)); bodies.push(body);
        if (conflict) { conflict = false; current.revision = 2; current.document_requirements![0].label_en = "Remote document label"; return reply({ error: { code: "version_conflict" } }, 409); }
        current = { ...current, ...body, revision: 3, document_requirements: body.document_requirements.map((entry: object) => ({ ...requirement, ...entry })) }; return reply(current);
      }
      return input === root ? reply({ items: [current] }) : reply(current);
    }));
    render(<ApplicationDefinitionWorkspace org={documentOrg} locale="en" permissions={permissions} />);
    const label = await screen.findByRole("textbox", { name: "English document label" });
    fireEvent.change(label, { target: { value: "Retained local document label" } });
    expect(screen.getByRole("button", { name: "Publish version" }).matches(":disabled")).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await screen.findByText("This definition changed elsewhere. Reload before editing again.");
    expect((screen.getByRole("textbox", { name: "English document label" }) as HTMLInputElement).value).toBe("Retained local document label");
    fireEvent.click(screen.getByRole("button", { name: "Load current saved definition" }));
    await screen.findByRole("heading", { name: "Current saved definition" });
    expect(screen.getByText(/Remote document label/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Use current revision and keep entered definition" }));
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await screen.findByText("Draft saved.");
    expect(bodies[1]).toMatchObject({ expected_revision: 2, document_requirements: [{ key: requirement.key, min_files: 1, max_files: 1, label_en: "Retained local document label", instructions_ta: requirement.instructions_ta }] });
  });

  it("requires the exact policy-view capability for nonempty definitions while preserving legacy access", async () => {
    vi.stubGlobal("fetch", vi.fn((input: string) => input === root ? reply({ items: [original] }) : reply({ items: [], next_cursor: null })));
    render(<ApplicationDefinitionWorkspace org={documentOrg} locale="en" permissions={permissions.filter(code => code !== "files.policy.view")} />);
    await screen.findByRole("textbox", { name: "English document label" });
    expect(screen.getByRole("textbox", { name: "English title" }).matches(":disabled")).toBe(true);
    expect(screen.queryByRole("button", { name: "Save draft" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Publish version" })).toBeNull();
    expect(screen.getByText("Viewing file policies is required to configure document requirements.")).toBeTruthy();
  });

  it("keeps a confirmed save when only the later version-list refresh fails", async () => {
    let saved = false;
    vi.stubGlobal("fetch", vi.fn((input: string, init?: RequestInit) => {
      if (input === "/api/session/csrf") return reply({ csrf_token: "csrf" });
      if (input.startsWith("/api/file-policies")) return reply({ items: [], next_cursor: null });
      if (init?.method === "PATCH") { saved = true; return reply({ ...original, title_en: "Confirmed title", revision: 2 }); }
      return saved ? reply({}, 503) : reply({ items: [original] });
    }));
    render(<ApplicationDefinitionWorkspace org={documentOrg} locale="en" permissions={permissions} />);
    fireEvent.change(await screen.findByRole("textbox", { name: "English title" }), { target: { value: "Confirmed title" } });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await screen.findByText("Saved. The version list could not be refreshed; reload it before switching versions.");
    expect((screen.getByRole("textbox", { name: "English title" }) as HTMLInputElement).value).toBe("Confirmed title");
    expect(screen.getByRole("button", { name: "Save draft" }).matches(":disabled")).toBe(true);
  });

  it("recovers lost creation with a read and never automatically creates another definition", async () => {
    let current: components["schemas"]["DefinitionView"] | null = null;
    let creations = 0;
    vi.stubGlobal("fetch", vi.fn((input: string, init?: RequestInit) => {
      if (input === "/api/session/csrf") return reply({ csrf_token: "csrf" });
      if (input.startsWith("/api/file-policies")) return reply({ items: [], next_cursor: null });
      if (init?.method === "POST") {
        creations++;
        const body = JSON.parse(String(init.body)) as components["schemas"]["DefinitionCreate"];
        current = {
          ...original, ...body, document_requirements: [],
          fields: body.fields.map((field, index) => ({
            ...field, id: `aaaaaaaa-aaaa-4aaa-8aaa-${String(index + 1).padStart(12, "0")}`, position: index + 1,
          })),
          acknowledgements: (body.acknowledgements ?? []).map((item, index) => ({
            ...item, id: `bbbbbbbb-bbbb-4bbb-8bbb-${String(index + 1).padStart(12, "0")}`, position: index + 1,
          })),
        };
        return Promise.reject(new Error("lost after create"));
      }
      return reply({ items: current ? [current] : [] });
    }));
    render(<ApplicationDefinitionWorkspace org={documentOrg} locale="en" permissions={permissions} />);
    await screen.findByText("No definition exists yet.");
    fireEvent.click(screen.getByRole("button", { name: "New definition" }));
    fireEvent.change(screen.getByRole("textbox", { name: "English title" }), { target: { value: "Entered title" } });
    fireEvent.change(screen.getByRole("textbox", { name: "Tamil title" }), { target: { value: "உள்ளிட்ட தலைப்பு" } });
    for (const control of screen.getAllByRole("textbox", { name: "English label" })) fireEvent.change(control, { target: { value: "Synthetic English text" } });
    for (const control of screen.getAllByRole("textbox", { name: "Tamil label" })) fireEvent.change(control, { target: { value: "செயற்கைத் தமிழ் உரை" } });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await screen.findByText("The change could not be confirmed. Read the saved definition before another command.");
    fireEvent.click(screen.getByRole("button", { name: "Load current saved definition" }));
    const region = await screen.findByRole("heading", { name: "Current saved definition" });
    expect(within(region.closest("article")!).getByText(/Entered title/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Use current revision and keep entered definition" }));
    await waitFor(() => expect((screen.getByRole("textbox", { name: "English title" }) as HTMLInputElement).value).toBe("Entered title"));
    expect(creations).toBe(1);
  });
});
