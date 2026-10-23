import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import FilePolicyWorkspace from "./view";
import { filePolicyWords, type FilePolicy } from "../../../../lib/file-policy-content";
const org = "11111111-1111-4111-8111-111111111111", id = "22222222-2222-4222-8222-222222222222", copiedId = "33333333-3333-4333-8333-333333333333";
const original: FilePolicy = { id, organization_id: org, client_request_id: id, purpose: "application_document", name: "Synthetic document rules", notice_en: "Synthetic notice only", notice_ta: "செயற்கை அறிவிப்பு மட்டும்", allowed_mime_types: ["application/pdf"], max_file_bytes: 2048, max_files: 2, retention_days: 30, rejected_retention_days: 3, allow_frozen_disposal: false, state: "draft", edition: 1, version: 1, copy_from: null, published_at: null, created_at: "2026-10-23T06:00:00Z", updated_at: "2026-10-23T06:00:00Z" };
const response = (value: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(value), { status }));
const rights = ["files.policy.view", "files.policy.manage"];
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
function mockApi(options: { empty?: boolean; published?: boolean; lostCreate?: boolean; conflict?: boolean; lostPublish?: boolean; failedListAfterWrite?: boolean; paging?: boolean } = {}) {
  let items: FilePolicy[] = options.empty ? [] : [{ ...original, ...(options.published ? { state: "published" as const, version: 2 } : {}) }];
  const writes: { path: string; body: Record<string, unknown> }[] = []; const reads: string[] = []; let failedList = false;
  vi.stubGlobal("fetch", vi.fn((input: string, init?: RequestInit) => {
    if (input === "/api/session/csrf") return response({ csrf_token: "csrf" });
    const [path, query] = input.split("?");
    if (!init?.method || init.method === "GET") {
      reads.push(input);
      if (query !== undefined) {
        if (options.failedListAfterWrite && writes.length && !failedList) { failedList = true; return response({}, 503); }
        return response({ items: query.includes("cursor=") ? [{ ...original, id: copiedId, name: "Later policy edition" }] : items, next_cursor: options.paging && !query.includes("cursor=") ? id : null });
      }
      return response(items.find(item => path.endsWith(item.id)) ?? {}, items.some(item => path.endsWith(item.id)) ? 200 : 404);
    }
    expect(new Headers(init.headers).get("x-csrf-token")).toBe("csrf");
    const body = JSON.parse(String(init.body)); writes.push({ path, body });
    if (path.endsWith("/policies")) {
      const existing = items.find(item => item.client_request_id === body.client_request_id);
      if (existing) return response(existing, 201);
      if (items.some(item => item.purpose === body.purpose && item.state === "draft")) return response({ error: { code: "file_policy_draft_exists" } }, 409);
      const value: FilePolicy = { ...original, ...body, id: copiedId, edition: items.length + 1 };
      items = [value, ...items];
      return options.lostCreate && writes.length === 1 ? Promise.reject(new Error("response lost after create")) : response(value, 201);
    }
    const index = items.findIndex(item => path.includes(item.id)); const item = items[index];
    if (options.conflict && writes.length === 1) { items[index] = { ...item, name: "Remote saved name", version: 2 }; return response({}, 409); }
    if (path.endsWith("publish")) items = items.map(value => value.id === item.id ? { ...value, state: "published", version: value.version + 1 } : value.state === "published" && value.purpose === item.purpose ? { ...value, state: "retired", version: value.version + 1 } : value);
    else if (path.endsWith("retire")) items[index] = { ...item, state: "retired", version: item.version + 1 };
    else items[index] = { ...item, ...body, version: item.version + 1 };
    if (options.lostPublish && writes.length === 1) return Promise.reject(new Error("response lost after publish"));
    return response(items.find(value => value.id === item.id));
  }));
  return { writes, reads };
}
async function open() { fireEvent.click(await screen.findByRole("button", { name: /Synthetic document rules/ })); await screen.findByDisplayValue(original.name); }
function change(label: string, value: string) { fireEvent.change(screen.getByLabelText(label), { target: { value } }); }
async function createFields() {
  fireEvent.click(await screen.findByRole("button", { name: "New policy draft" }));
  change("File purpose", "application_document"); change("Policy name", "Explicit synthetic policy"); change("English notice", "Synthetic EN notice"); change("Tamil notice", "செயற்கை தமிழ் அறிவிப்பு");
  fireEvent.click(screen.getByLabelText("application/pdf")); change("Maximum file size (bytes)", "4096"); change("Maximum files", "2"); change("Retention (days)", "30"); change("Rejected-file retention (days)", "3"); change("Disposal of frozen evidence", "false"); change("Change reason", "Synthetic draft configuration");
}
describe("configurable policy administration", () => {
  it("starts with no invented purpose, MIME, retention or disposal defaults", async () => {
    mockApi({ empty: true }); render(<FilePolicyWorkspace org={org} locale="en" permissions={rights} />);
    await waitFor(() => expect((screen.getByRole("button", { name: "New policy draft" }) as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(screen.getByRole("button", { name: "New policy draft" }));
    for (const label of ["File purpose", "Policy name", "English notice", "Tamil notice", "Maximum file size (bytes)", "Maximum files", "Retention (days)", "Rejected-file retention (days)", "Disposal of frozen evidence"]) expect((screen.getByLabelText(label) as HTMLInputElement).value).toBe("");
    expect((screen.getByLabelText("application/pdf") as HTMLInputElement).checked).toBe(false);
    expect(screen.queryByRole("button", { name: "Publish policy edition" })).toBeNull(); expect(screen.queryByRole("button", { name: /Upload/ })).toBeNull();
  });
  it("recovers an uncertain creation with exactly the frozen request and UUID, without automatic publication", async () => {
    const api = mockApi({ empty: true, lostCreate: true }); render(<FilePolicyWorkspace org={org} locale="en" permissions={rights} />);
    await waitFor(() => expect((screen.getByRole("button", { name: "New policy draft" }) as HTMLButtonElement).disabled).toBe(false));
    await createFields(); fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await screen.findByText(filePolicyWords.en.uncertainCreate); expect(api.writes).toHaveLength(1); expect(screen.getByLabelText("Policy name").matches(":disabled")).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Retry the same draft request" })); await screen.findByText("Saved.");
    expect(api.writes).toHaveLength(2); expect(api.writes[1].body).toEqual(api.writes[0].body); expect(api.writes[0].body.client_request_id).toMatch(/^[0-9a-f-]{36}$/);
    expect(api.writes[0].body).toMatchObject({ allow_frozen_disposal: false, retention_days: 30, rejected_retention_days: 3, max_files: 2 });
    expect(api.writes.some(write => write.path.endsWith("publish"))).toBe(false);
    expect((screen.getByRole("button", { name: "Publish policy edition" }) as HTMLButtonElement).disabled).toBe(true);
  });
  it("keeps entered rules after a definite existing-draft conflict without retrying or publishing", async () => {
    const api = mockApi(); render(<FilePolicyWorkspace org={org} locale="en" permissions={rights} />);
    await waitFor(() => expect((screen.getByRole("button", { name: "New policy draft" }) as HTMLButtonElement).disabled).toBe(false));
    await createFields(); fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await screen.findByText(filePolicyWords.en.draftExists); expect(api.writes).toHaveLength(1);
    expect((screen.getByLabelText("Policy name") as HTMLInputElement).value).toBe("Explicit synthetic policy");
    expect(screen.getByLabelText("Policy name").matches(":disabled")).toBe(false); expect(screen.queryByRole("button", { name: "Retry the same draft request" })).toBeNull();
  });
  it("preserves entered rules through conflict review and writes only after explicit current-version selection", async () => {
    const api = mockApi({ conflict: true }); render(<FilePolicyWorkspace org={org} locale="en" permissions={rights} />); await open();
    change("Policy name", "My retained rules"); change("Change reason", "Synthetic update"); fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await screen.findByText(filePolicyWords.en.conflict); expect(api.writes).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "Load current saved edition" }));
    const current = (await screen.findByRole("heading", { name: "Current saved edition" })).closest("article")!;
    expect(within(current).getByText(/Remote saved name/)).toBeTruthy();
    expect((screen.getByLabelText("Policy name") as HTMLInputElement).value).toBe("My retained rules");
    fireEvent.click(screen.getByRole("button", { name: "Use current version and keep entered rules" })); fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await screen.findByText("Saved."); expect(api.writes[1].body).toMatchObject({ expected_version: 2, name: "My retained rules" });
  });
  it("reconciles a lost publication response without replaying publication and retains immutable rules", async () => {
    const api = mockApi({ lostPublish: true }); render(<FilePolicyWorkspace org={org} locale="en" permissions={rights} />); await open();
    change("Change reason", "Publish synthetic rules"); fireEvent.click(screen.getByRole("button", { name: "Publish policy edition" })); await screen.findByText(filePolicyWords.en.uncertain);
    expect(api.writes).toHaveLength(1); fireEvent.click(screen.getByRole("button", { name: "Load current saved edition" }));
    await screen.findByRole("button", { name: "Use current version and keep entered rules" }); fireEvent.click(screen.getByRole("button", { name: "Use current version and keep entered rules" }));
    expect(api.writes).toHaveLength(1); expect(screen.queryByRole("button", { name: "Publish policy edition" })).toBeNull(); expect(screen.getByLabelText("Policy name").matches(":disabled")).toBe(true);
  });
  it("copies published rules into a new purpose-pinned draft and requires an explicit new reason", async () => {
    const api = mockApi({ published: true }); render(<FilePolicyWorkspace org={org} locale="en" permissions={rights} />); await open();
    expect(screen.getByLabelText("Policy name").matches(":disabled")).toBe(true); fireEvent.click(screen.getByRole("button", { name: "Copy displayed rules to a new edition" }));
    expect((screen.getByLabelText("File purpose") as HTMLSelectElement).disabled).toBe(true); expect((screen.getByLabelText("Change reason") as HTMLTextAreaElement).value).toBe("");
    change("Policy name", "Revised edition"); change("Change reason", "New synthetic edition"); fireEvent.click(screen.getByRole("button", { name: "Save draft" })); await screen.findByText("Saved.");
    expect(api.writes[0].body).toMatchObject({ copy_from: id, purpose: "application_document", name: "Revised edition" });
    expect(api.writes[0].body).not.toHaveProperty("state"); expect(api.writes).toHaveLength(1);
  });
  it("reports a confirmed save separately from a later list-refresh failure", async () => {
    const api = mockApi({ failedListAfterWrite: true }); render(<FilePolicyWorkspace org={org} locale="en" permissions={rights} />); await open();
    change("Policy name", "Confirmed saved policy"); change("Change reason", "Synthetic save"); fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await screen.findByText(filePolicyWords.en.savedRefresh); expect(api.writes).toHaveLength(1); expect((screen.getByLabelText("Change reason") as HTMLTextAreaElement).value).toBe("");
    fireEvent.click(screen.getByRole("button", { name: "Refresh list" })); await waitFor(() => expect(api.reads.length).toBeGreaterThan(3)); expect(api.writes).toHaveLength(1);
  });
  it("keeps narrow viewers read-only and paginates via bounded cursor requests", async () => {
    const api = mockApi({ paging: true }); render(<FilePolicyWorkspace org={org} locale="en" permissions={["files.policy.view"]} />); await open();
    expect((screen.getByRole("button", { name: "New policy draft" }) as HTMLButtonElement).disabled).toBe(true); expect(screen.getByLabelText("Policy name").matches(":disabled")).toBe(true);
    expect(screen.queryByRole("button", { name: "Publish policy edition" })).toBeNull(); expect(screen.queryByRole("button", { name: "Retire policy edition" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Load more" })); await screen.findByRole("button", { name: /Later policy edition/ }); expect(api.reads).toContain(`/api/file-policies/organizations/${org}/policies?limit=25&cursor=${id}`);
  });
  it("renders Tamil purpose, rule and retention controls", async () => {
    mockApi(); render(<FilePolicyWorkspace org={org} locale="ta" permissions={rights} />); fireEvent.click(await screen.findByRole("button", { name: /Synthetic document rules/ }));
    expect(await screen.findByLabelText(filePolicyWords.ta.notice_ta)).toBeTruthy(); expect(screen.getByLabelText(filePolicyWords.ta.retention_days)).toBeTruthy(); expect(within(screen.getByRole("region", { name: filePolicyWords.ta.details })).getByText(filePolicyWords.ta.publicationNote)).toBeTruthy();
  });
});
