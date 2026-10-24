import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import type { components } from "../lib/api-contracts";
import { AssignmentFiles, TrainerSubmissionFiles } from "./learning-assignment-files";
import { AssignmentRuleEditor, LearningMaterialManager } from "./learning-file-authoring";
import { LearningFileUpload } from "./learning-file-upload";
import { learningFileWords } from "../lib/learning-file-messages";

type Item = components["schemas"]["AssignmentFileView"];
type Rule = components["schemas"]["AssignmentFileRuleView"];
type Material = components["schemas"]["MaterialFileView"];
type Course = components["schemas"]["AdminCourseView"];
const org = "11111111-1111-4111-8111-111111111111";
const courseId = "22222222-2222-4222-8222-222222222222";
const id = "33333333-3333-4333-8333-333333333333";
const other = "44444444-4444-4444-8444-444444444444";
const lessonId = "55555555-5555-4555-8555-555555555555";
const root = `/api/courses/organizations/${org}`;
const path = root + `/my-learning/${courseId}/assignments/${id}/files`;
const rulePath = root + `/courses/${courseId}/assignments/${id}/file-rule`;
const time = "2026-10-23T08:00:00Z";
const text = learningFileWords.en;
const json = (data: unknown, status = 200) => Response.json(data, { status });
function item(change: Partial<Item> = {}): Item {
  return { id, target_revision: 1, state: "active", version: 3, usable: false, submission_id: null, evidence: null,
    file: { id: other, organization_id: org, owner_person_id: other, purpose: "assignment_submission", resource_id: id,
      policy_id: org, client_request_id: id, media_type: "application/pdf", byte_size: 14, sha256: "0".repeat(64),
      state: "pending", version: 7, verified_at: null, scanned_at: null, scan_attempts: 0, failure_code: null,
      retention_until: "2099-01-01T00:00:00Z", legal_hold: false, evidence_frozen: false, deleted_at: null,
      created_at: time, updated_at: time }, ...change };
}
const clean = item({ usable: true, file: { ...item().file, state: "clean" } });
const rule: Rule = { policy_id: org, minimum_files: 1, maximum_files: 2, version: 4,
  allowed_mime_types: ["application/pdf"], max_file_bytes: 2048, notice_en: "Synthetic learning notice", notice_ta: "செயற்கை அறிவிப்பு" };
const batch = (items: Item[], fileRule: Rule | null = rule) => ({ collection_enabled: true, max_upload_bytes: 1024, next_revision: 1, rule: fileRule, items });
const policy = { id: org, organization_id: org, client_request_id: id, purpose: "assignment_submission", name: "Synthetic policy",
  notice_en: "Synthetic learning notice", notice_ta: "செயற்கை அறிவிப்பு", allowed_mime_types: ["application/pdf"], max_file_bytes: 2048,
  max_files: 2, retention_days: 1, rejected_retention_days: 1, allow_frozen_disposal: false, state: "published", edition: 2,
  version: 2, copy_from: null, published_at: time, created_at: time, updated_at: time };
const course: Course = { id: courseId, organization_id: org, created_at: time, updated_at: time, code: "SYNTH", title_en: "Synthetic course", title_ta: "செயற்கை பாடம்",
  description_en: "Synthetic description", description_ta: "செயற்கை விளக்கம்", state: "draft", version: 1,
  completion_rule: "all_lessons", minimum_lessons: null, published_at: null, modules: [{ id: other, course_id: courseId, organization_id: org, created_at: time, position: 1,
    title_en: "Synthetic module", title_ta: "செயற்கை தொகுதி", lessons: [{ id: lessonId, course_id: courseId, module_id: other, organization_id: org, created_at: time, position: 1,
      title_en: "Synthetic lesson", title_ta: "செயற்கை பகுதி", body_en: "Synthetic", body_ta: "செயற்கை",
      duration_minutes: null, prerequisite_lesson_ids: [], materials: [], quizzes: [], assignments: [] }] }] };
const material = (change: Partial<Material> = {}): Material => ({ material_id: id, version: 3, state: "active",
  file: { ...item().file, purpose: "lms_material" }, evidence: null, usable: false, ...change });
function source(name = "synthetic.pdf") {
  return Object.assign(new File(["%PDF-synthetic"], name, { type: "application/pdf" }), {
    arrayBuffer: async () => new TextEncoder().encode("%PDF-synthetic").buffer,
  });
}
function cryptoMock() { vi.stubGlobal("crypto", { randomUUID: () => id, subtle: { digest: async () => new Uint8Array(32).buffer } }); }
afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("learning file uploads and recovery", () => {
  it("freezes the UUID and metadata for a lost-create retry, then uploads only once", async () => {
    cryptoMock(); let attempts = 0;
    const api = vi.fn(async (url: string, init?: RequestInit) => {
      if (url === "/api/session/csrf") return json({ csrf_token: "csrf" });
      if (init?.method === "POST") { if (++attempts === 1) throw new Error("lost after commit"); return json(item(), 201); }
      if (init?.method === "PUT") return json(item({ file: { ...item().file, state: "quarantined", version: 9 } }));
      return json(item());
    }); vi.stubGlobal("fetch", api);
    const saved = vi.fn();
    render(<LearningFileUpload<Item> locale="en" enabled allowed={["application/pdf"]} maxBytes={1024} createPath={path}
      intent={(metadata, requestId) => ({ ...metadata, client_request_id: requestId, expected_revision: 1 })}
      detailPath={() => path + `/${id}`} onSaved={saved} />);
    fireEvent.change(screen.getByLabelText(text.select), { target: { files: [source()] } });
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: text.upload })); });
    expect(screen.getByLabelText(text.select)).toHaveProperty("disabled", true);
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: text.recoverCreate })); });
    const posts = api.mock.calls.filter(call => call[1]?.method === "POST");
    expect(posts).toHaveLength(2); expect(posts[0][1]?.body).toBe(posts[1][1]?.body);
    expect(JSON.parse(String(posts[0][1]?.body))).toMatchObject({ client_request_id: id, expected_revision: 1, byte_size: 14 });
    const writes = api.mock.calls.filter(call => call[1]?.method === "PUT");
    expect(writes).toHaveLength(1); expect(new Headers(writes[0][1]?.headers).get("if-match")).toBe('"7"');
    expect(saved).toHaveBeenCalledTimes(1); expect(screen.getByText(text.scanning)).toBeTruthy();
  });

  it("reads a lost committed PUT before permitting a resend and never duplicates accepted bytes", async () => {
    cryptoMock();
    const api = vi.fn(async (url: string, init?: RequestInit) => {
      if (url === "/api/session/csrf") return json({ csrf_token: "csrf" });
      if (init?.method === "POST") return json(item(), 201);
      if (init?.method === "PUT") throw new Error("lost response");
      return json(item({ file: { ...item().file, state: "quarantined", version: 9 } }));
    }); vi.stubGlobal("fetch", api);
    render(<LearningFileUpload<Item> locale="en" enabled allowed={["application/pdf"]} maxBytes={1024} createPath={path}
      intent={(metadata, requestId) => ({ ...metadata, client_request_id: requestId })} detailPath={() => path + `/${id}`} onSaved={vi.fn()} />);
    fireEvent.change(screen.getByLabelText(text.select), { target: { files: [source()] } });
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: text.upload })); });
    expect(screen.queryByRole("button", { name: text.resend })).toBeNull();
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: text.review })); });
    expect(api.mock.calls.filter(call => call[1]?.method === "PUT")).toHaveLength(1);
    expect(screen.queryByRole("button", { name: text.resend })).toBeNull();
    expect(screen.getByText(text.scanning)).toBeTruthy();
  });

  it("requires an explicit resend after a pending read and uses its fresh file version", async () => {
    cryptoMock(); let writes = 0;
    const api = vi.fn(async (url: string, init?: RequestInit) => {
      if (url === "/api/session/csrf") return json({ csrf_token: "csrf" });
      if (init?.method === "POST") return json(item(), 201);
      if (init?.method === "PUT") { if (++writes === 1) throw new Error("lost before upload"); return json(clean); }
      return json(item({ file: { ...item().file, version: 12 } }));
    }); vi.stubGlobal("fetch", api);
    render(<LearningFileUpload<Item> locale="en" enabled allowed={["application/pdf"]} maxBytes={1024} createPath={path}
      intent={metadata => metadata} detailPath={() => path + `/${id}`} onSaved={vi.fn()} />);
    fireEvent.change(screen.getByLabelText(text.select), { target: { files: [source()] } });
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: text.upload })); });
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: text.review })); });
    expect(writes).toBe(1);
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: text.resend })); });
    const last = api.mock.calls.filter(call => call[1]?.method === "PUT").at(-1)!;
    expect(new Headers(last[1]?.headers).get("if-match")).toBe('"12"');
  });

  it("enforces operational byte limits before metadata creation and exact hashes on resume", async () => {
    cryptoMock(); const api = vi.fn(); vi.stubGlobal("fetch", api);
    const { rerender } = render(<LearningFileUpload<Item> locale="en" enabled allowed={["application/pdf"]} maxBytes={10}
      createPath={path} intent={metadata => metadata} detailPath={() => path + `/${id}`} onSaved={vi.fn()} />);
    fireEvent.change(screen.getByLabelText(text.select), { target: { files: [source()] } });
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: text.upload })); });
    expect(api).not.toHaveBeenCalled(); expect(screen.getByText(text.invalid)).toBeTruthy();
    rerender(<LearningFileUpload<Item> locale="en" enabled allowed={["application/pdf"]} maxBytes={1024}
      createPath={path} resume={item({ file: { ...item().file, sha256: "a".repeat(64) } })}
      intent={metadata => metadata} detailPath={() => path + `/${id}`} onSaved={vi.fn()} />);
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: text.upload })); });
    expect(api).not.toHaveBeenCalled(); expect(screen.getByText(text.sourceMismatch)).toBeTruthy();
  });

  it("keeps an interrupted uploading lease and original bytes recoverable until explicit resend", async () => {
    cryptoMock(); let writes = 0;
    const api = vi.fn(async (url: string, init?: RequestInit) => {
      if (url === "/api/session/csrf") return json({ csrf_token: "csrf" });
      if (init?.method === "POST") return json(item(), 201);
      if (init?.method === "PUT") { if (++writes === 1) throw new Error("connection interrupted"); return json(clean); }
      return json(item({ file: { ...item().file, state: "uploading", version: 8 } }));
    }); vi.stubGlobal("fetch", api);
    render(<LearningFileUpload<Item> locale="en" enabled allowed={["application/pdf"]} maxBytes={1024} createPath={path}
      intent={metadata => metadata} detailPath={() => path + `/${id}`} onSaved={vi.fn()} />);
    fireEvent.change(screen.getByLabelText(text.select), { target: { files: [source()] } });
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: text.upload })); });
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: text.review })); });
    expect(screen.getByText("synthetic.pdf · 14 bytes")).toBeTruthy(); expect(writes).toBe(1);
    expect(screen.getByRole("button", { name: text.resend })).toBeTruthy();
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: text.resend })); });
    expect(writes).toBe(2); expect(screen.getByText(text.saved)).toBeTruthy();
  });
});

describe("learner and trainer evidence", () => {
  it("requires explicit usable selections, enforces minimum, and does not select expired clean files", async () => {
    const ready = vi.fn(); vi.stubGlobal("fetch", vi.fn(async () => json(batch([clean, { ...clean, id: other, usable: false }]))));
    await act(async () => { render(<form data-testid="assignment"><AssignmentFiles org={org} courseId={courseId} assignmentId={id}
      locale="en" editable refreshKey="" onReady={ready} /></form>); });
    const boxes = screen.getAllByRole("checkbox");
    expect(boxes[0]).toHaveProperty("checked", false); expect(boxes[1]).toHaveProperty("disabled", true);
    expect(ready).toHaveBeenLastCalledWith(false);
    fireEvent.click(boxes[0]); expect(ready).toHaveBeenLastCalledWith(true);
    expect(new FormData(screen.getByTestId("assignment") as HTMLFormElement).getAll("file_ids")).toEqual([id]);
    expect(screen.getAllByRole("link")).toHaveLength(1);
    expect(screen.getByText(/Maximum upload bytes: 1024/)).toBeTruthy();
  });

  it("keeps text-only assignments available when collection is off and no rule exists", async () => {
    const ready = vi.fn(); vi.stubGlobal("fetch", vi.fn(async () => json({ ...batch([], null), collection_enabled: false })));
    await act(async () => { render(<AssignmentFiles org={org} courseId={courseId} assignmentId={id} locale="ta" editable refreshKey="" onReady={ready} />); });
    expect(ready).toHaveBeenLastCalledWith(true); expect(screen.getByText(learningFileWords.ta.noRule)).toBeTruthy();
    expect(screen.queryByLabelText(learningFileWords.ta.select)).toBeNull();
  });

  it("blocks configured required evidence and byte links while collection is disabled", async () => {
    const ready = vi.fn(); vi.stubGlobal("fetch", vi.fn(async () => json({ ...batch([clean]), collection_enabled: false })));
    await act(async () => { render(<AssignmentFiles org={org} courseId={courseId} assignmentId={id} locale="en" editable refreshKey="" onReady={ready} />); });
    expect(ready).toHaveBeenLastCalledWith(false); expect(screen.getByRole("checkbox")).toHaveProperty("disabled", true);
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("preserves local file selection after a failed refresh while blocking submission", async () => {
    let fail = false; const ready = vi.fn(); vi.stubGlobal("fetch", vi.fn(async () => { if (fail) throw new Error("network"); return json(batch([])); }));
    await act(async () => { render(<AssignmentFiles org={org} courseId={courseId} assignmentId={id} locale="en" editable refreshKey="" onReady={ready} />); });
    fail = true;
    // Start the read before choosing a file; its late failure must not unmount the uploader.
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: text.refresh })); });
    fireEvent.change(screen.getByLabelText(text.select), { target: { files: [source()] } });
    expect(screen.getByText("synthetic.pdf · 14 bytes")).toBeTruthy(); expect(ready).toHaveBeenLastCalledWith(false);
    expect(screen.getByRole("button", { name: text.upload })).toHaveProperty("disabled", true);
  });

  it("uses binding versions for removal and reconciles lost DELETE without automatically deleting again", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true); let removed = false;
    const api = vi.fn(async (url: string, init?: RequestInit) => {
      if (url === "/api/session/csrf") return json({ csrf_token: "csrf" });
      if (init?.method === "DELETE") { removed = true; throw new Error("lost delete response"); }
      if (url === path + `/${id}`) return json({ ...clean, state: "removed" });
      return json(batch(removed ? [] : [clean]));
    }); vi.stubGlobal("fetch", api);
    await act(async () => { render(<AssignmentFiles org={org} courseId={courseId} assignmentId={id} locale="en" editable refreshKey="" onReady={vi.fn()} />); });
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: text.remove })); });
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: text.review })); });
    const deletes = api.mock.calls.filter(call => call[1]?.method === "DELETE");
    expect(deletes).toHaveLength(1); expect(deletes[0][1]?.body).toBe('{"expected_version":3}');
    expect(screen.queryByRole("checkbox")).toBeNull();
  });

  it("polls only reads, stops after twenty checks and never promotes scan errors to clean", async () => {
    vi.useFakeTimers(); const ready = vi.fn(); const api = vi.fn(async () => json(batch([item({ file: { ...item().file, state: "quarantined", failure_code: "scan_unavailable" } })])));
    vi.stubGlobal("fetch", api);
    await act(async () => { render(<AssignmentFiles org={org} courseId={courseId} assignmentId={id} locale="en" editable refreshKey="" onReady={ready} />); });
    for (let attempt = 0; attempt < 20; attempt++) await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    expect(api).toHaveBeenCalledTimes(21); expect(screen.getByText(text.pollStopped)).toBeTruthy();
    await act(async () => { await vi.advanceTimersByTimeAsync(60000); }); expect(api).toHaveBeenCalledTimes(21);
    expect(ready).toHaveBeenLastCalledWith(false); expect(screen.queryByRole("link")).toBeNull();
  });

  it("renders trainer links only for usable frozen evidence and clears them after access revocation", async () => {
    let revoked = false;
    vi.stubGlobal("fetch", vi.fn(async () => revoked ? json({}, 403) : json([
      { ...clean, state: "submitted", evidence: { file_id: other, file_version: 5, sha256: "a".repeat(64), byte_size: 14, frozen_at: time } },
      { ...clean, id: other, usable: false, evidence: { file_id: id, file_version: 3, sha256: "b".repeat(64), byte_size: 14, frozen_at: time } },
    ])));
    await act(async () => { render(<TrainerSubmissionFiles org={org} courseId={courseId} submissionId={id} locale="ta" />); });
    expect(screen.getAllByRole("link")).toHaveLength(1);
    expect(screen.getByRole("link").getAttribute("href")).toBe(root + `/trainer-delivery/${courseId}/assignment-submissions/${id}/files/${id}/content`);
    revoked = true; await act(async () => { fireEvent.click(screen.getByRole("button", { name: learningFileWords.ta.refresh })); });
    expect(screen.queryByRole("link")).toBeNull(); expect(screen.getByText(learningFileWords.ta.error)).toBeTruthy();
  });

  it("ignores an old trainer success after the requested course scope has changed", async () => {
    let resolveOld!: (response: Response) => void;
    const slow = new Promise<Response>(resolve => { resolveOld = resolve; });
    vi.stubGlobal("fetch", vi.fn(async (url: string) => url.includes(`/trainer-delivery/${courseId}/`) ? slow : json({}, 403)));
    let view!: ReturnType<typeof render>;
    await act(async () => { view = render(<TrainerSubmissionFiles org={org} courseId={courseId} submissionId={id} locale="en" />); });
    await act(async () => { view.rerender(<TrainerSubmissionFiles org={org} courseId={other} submissionId={id} locale="en" />); });
    await act(async () => { resolveOld(json([{ ...clean, state: "submitted", evidence: { file_id: other, file_version: 5, sha256: "a".repeat(64), byte_size: 14, frozen_at: time } }])); });
    expect(screen.queryByRole("link")).toBeNull(); expect(screen.getByText(text.error)).toBeTruthy();
  });
});

describe("draft authoring with explicit policy rules", () => {
  it("starts with blank requirements and sends explicit counts without inventing defaults", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const api = vi.fn(async (url: string, init?: RequestInit) => url === "/api/session/csrf" ? json({ csrf_token: "csrf" })
      : url.startsWith("/api/file-policies") ? json({ items: [policy], next_cursor: null })
        : init?.method === "PUT" ? json({ ...rule, version: 1 }) : json(null));
    vi.stubGlobal("fetch", api);
    await act(async () => { render(<AssignmentRuleEditor org={org} courseId={courseId} assignmentId={id} locale="en" editable canViewPolicies onDirty={vi.fn()} onSaved={async () => {}} />); });
    expect(screen.getByLabelText(text.policy)).toHaveProperty("value", "");
    expect(screen.getByLabelText(text.minimum)).toHaveProperty("value", ""); expect(screen.getByLabelText(text.maximum)).toHaveProperty("value", "");
    fireEvent.change(screen.getByLabelText(text.policy), { target: { value: org } });
    fireEvent.change(screen.getByLabelText(text.minimum), { target: { value: "0" } });
    fireEvent.change(screen.getByLabelText(text.maximum), { target: { value: "2" } });
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: text.configure })); });
    const write = api.mock.calls.find(call => call[1]?.method === "PUT")!;
    expect(write[0]).toBe(rulePath); expect(JSON.parse(String(write[1]?.body))).toEqual({ policy_id: org, minimum_files: 0, maximum_files: 2, expected_version: null });
  });

  it("retains edited counts after conflict until latest version is read and explicitly accepted", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true); let writes = 0;
    const api = vi.fn(async (url: string, init?: RequestInit) => {
      if (url === "/api/session/csrf") return json({ csrf_token: "csrf" });
      if (url.startsWith("/api/file-policies")) return json({ items: [policy], next_cursor: null });
      if (init?.method === "PUT") { if (++writes === 1) return json({}, 409); return json({ ...rule, minimum_files: 0, version: 6 }); }
      return json({ ...rule, version: writes ? 5 : 4 });
    }); vi.stubGlobal("fetch", api);
    await act(async () => { render(<AssignmentRuleEditor org={org} courseId={courseId} assignmentId={id} locale="en" editable canViewPolicies onDirty={vi.fn()} onSaved={async () => {}} />); });
    fireEvent.change(screen.getByLabelText(text.minimum), { target: { value: "0" } });
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: text.configure })); });
    expect(screen.getByLabelText(text.minimum)).toHaveProperty("value", "0");
    expect(screen.getByRole("button", { name: text.configure })).toHaveProperty("disabled", true);
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: text.reviewRule })); });
    expect(writes).toBe(1); fireEvent.click(screen.getByRole("button", { name: text.acceptVersion }));
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: text.configure })); });
    const last = api.mock.calls.filter(call => call[1]?.method === "PUT").at(-1)!;
    expect(JSON.parse(String(last[1]?.body))).toMatchObject({ minimum_files: 0, expected_version: 5 });
  });

  it("does not fetch privileged policies or expose controls for published rules", async () => {
    const api = vi.fn(async () => json(rule)); vi.stubGlobal("fetch", api);
    await act(async () => { render(<AssignmentRuleEditor org={org} courseId={courseId} assignmentId={id} locale="en" editable={false} canViewPolicies={false} onDirty={vi.fn()} onSaved={async () => {}} />); });
    expect(api).toHaveBeenCalledTimes(1); expect(screen.getByText(text.readOnly)).toBeTruthy(); expect(screen.queryByRole("combobox")).toBeNull();
  });

  it("never blocks draft publication because an unrelated published rule read failed", async () => {
    const dirty = vi.fn(); vi.stubGlobal("fetch", vi.fn(async () => json({}, 503)));
    await act(async () => { render(<AssignmentRuleEditor org={org} courseId={courseId} assignmentId={id} locale="en"
      editable={false} canViewPolicies onDirty={dirty} onSaved={async () => {}} />); });
    expect(dirty).toHaveBeenLastCalledWith(false); expect(screen.getByText(text.error)).toBeTruthy();
  });

  it("retries failed policy reads without losing entered material labels", async () => {
    let reads = 0;
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      if (url.startsWith("/api/file-policies")) return ++reads === 1 ? json({}, 503) : json({ items: [policy], next_cursor: null });
      return json({ collection_enabled: true, max_upload_bytes: 1024, items: [], next_cursor: null });
    }));
    await act(async () => { render(<LearningMaterialManager org={org} course={course} locale="en" canUpload externalBusy={false} onDirty={vi.fn()} onSaved={async () => {}} />); });
    fireEvent.change(screen.getByLabelText(text.labelEn), { target: { value: "Preserved local label" } });
    const refreshes = screen.getAllByRole("button", { name: text.refresh });
    await act(async () => { fireEvent.click(refreshes[1]); });
    expect(reads).toBe(2); expect(screen.getByLabelText(text.labelEn)).toHaveProperty("value", "Preserved local label");
    expect(screen.getByRole("option", { name: /Synthetic policy/ })).toBeTruthy();
  });

  it("creates private materials with explicit bilingual labels and bounded upload metadata", async () => {
    cryptoMock();
    const api = vi.fn(async (url: string, init?: RequestInit) => {
      if (url === "/api/session/csrf") return json({ csrf_token: "csrf" });
      if (url.startsWith("/api/file-policies")) return json({ items: [{ ...policy, purpose: "lms_material" }], next_cursor: null });
      if (init?.method === "POST") return json(material(), 201);
      if (init?.method === "PUT") return json(material({ file: { ...material().file, state: "quarantined" } }));
      return json({ collection_enabled: true, max_upload_bytes: 1024, items: [], next_cursor: null });
    }); vi.stubGlobal("fetch", api);
    await act(async () => { render(<LearningMaterialManager org={org} course={course} locale="en" canUpload externalBusy={false} onDirty={vi.fn()} onSaved={async () => {}} />); });
    fireEvent.change(screen.getByLabelText(text.lesson), { target: { value: lessonId } });
    fireEvent.change(screen.getByLabelText(text.policy), { target: { value: org } });
    fireEvent.change(screen.getByLabelText(text.position), { target: { value: "3" } });
    fireEvent.change(screen.getByLabelText(text.labelEn), { target: { value: "Synthetic handout" } });
    fireEvent.change(screen.getByLabelText(text.labelTa), { target: { value: "செயற்கை கையேடு" } });
    fireEvent.change(screen.getByLabelText(text.select), { target: { files: [source()] } });
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: text.upload })); });
    const post = api.mock.calls.find(call => call[1]?.method === "POST")!;
    expect(post[0]).toBe(root + "/material-files");
    expect(JSON.parse(String(post[1]?.body))).toMatchObject({ client_request_id: id, policy_id: org, course_id: courseId,
      lesson_id: lessonId, position: 3, label_en: "Synthetic handout", label_ta: "செயற்கை கையேடு", byte_size: 14 });
    expect(screen.queryByLabelText(/provider/i)).toBeNull(); expect(screen.getByLabelText(text.labelEn)).toHaveProperty("value", "");
  });

  it("removes a draft material with its binding version, keeps history, and hides removed downloads", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true); let removed = false;
    const api = vi.fn(async (url: string, init?: RequestInit) => {
      if (url === "/api/session/csrf") return json({ csrf_token: "csrf" });
      if (url.startsWith("/api/file-policies")) return json({ items: [], next_cursor: null });
      if (init?.method === "DELETE") { removed = true; return json(material({ state: "removed", version: 4 })); }
      return json({ collection_enabled: true, max_upload_bytes: 1024, items: [material({ state: removed ? "removed" : "active" })], next_cursor: null });
    }); vi.stubGlobal("fetch", api);
    await act(async () => { render(<LearningMaterialManager org={org} course={course} locale="en" canUpload externalBusy={false} onDirty={vi.fn()} onSaved={async () => {}} />); });
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: text.remove })); });
    const write = api.mock.calls.find(call => call[1]?.method === "DELETE")!;
    expect(write[0]).toBe(root + `/courses/${courseId}/material-files/${id}`); expect(write[1]?.body).toBe('{"expected_version":3}');
    expect(screen.getByText(text.removed)).toBeTruthy(); expect(screen.queryByRole("link")).toBeNull();
    expect(within(screen.getByRole("list")).queryByRole("button", { name: text.remove })).toBeNull();
  });
});
