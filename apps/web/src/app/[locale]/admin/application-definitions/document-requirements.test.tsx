import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import DocumentRequirementsEditor from "./document-requirements";
import { applicationDocumentWords, newDocumentRequirement, serializeDocumentRequirements, type DraftDocumentRequirement } from "../../../../lib/application-document-content";
import type { FilePolicy } from "../../../../lib/file-policy-content";

const org = "11111111-1111-4111-8111-111111111111", policyId = "22222222-2222-4222-8222-222222222222";
const policy: FilePolicy = { id: policyId, organization_id: org, client_request_id: policyId, purpose: "application_document", name: "Synthetic policy", notice_en: "Synthetic English notice", notice_ta: "செயற்கை அறிவிப்பு", allowed_mime_types: ["application/pdf"], max_file_bytes: 4096, max_files: 2, retention_days: 30, rejected_retention_days: 3, allow_frozen_disposal: false, edition: 1, version: 2, state: "published", copy_from: null, published_at: "2026-10-23T08:00:00Z", created_at: "2026-10-23T07:00:00Z", updated_at: "2026-10-23T08:00:00Z" };
const reply = (items: FilePolicy[], next_cursor: string | null = null) => Promise.resolve(Response.json({ items, next_cursor }));
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

function Harness({ initial = [], locale = "en", canView = true }: { initial?: DraftDocumentRequirement[]; locale?: "en" | "ta"; canView?: boolean }) {
  const [values, setValues] = useState(initial);
  return <DocumentRequirementsEditor org={org} locale={locale} values={values} onChange={setValues} disabled={false} canViewPolicies={canView} />;
}

describe("configurable application document requirements", () => {
  it("starts without requirements and requires explicit policy and file counts", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => reply([policy])));
    render(<Harness />);
    expect(screen.getByText("This form has no document requirements.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Add document requirement" }));
    expect((screen.getByRole("textbox", { name: "English document label" }) as HTMLInputElement).value).toBe("");
    expect((screen.getByRole("textbox", { name: "Tamil document label" }) as HTMLInputElement).value).toBe("");
    expect((screen.getByRole("spinbutton", { name: "Minimum files" }) as HTMLInputElement).value).toBe("");
    expect((screen.getByRole("spinbutton", { name: "Maximum files" }) as HTMLInputElement).value).toBe("");
    expect((screen.getByRole("combobox", { name: "Published file policy edition" }) as HTMLSelectElement).value).toBe("");
    await screen.findByRole("option", { name: "Synthetic policy · Edition 1" });
    expect(screen.getByText("Configure only approved requirements. Publishing this form does not enable file collection.")).toBeTruthy();
  });

  it("retains existing retired pins, paginates published choices and preserves edits on a failed refresh", async () => {
    let failure = false;
    const fetchMock = vi.fn((input: string) => failure ? Promise.resolve(Response.json({}, { status: 503 })) : input.includes("cursor=") ? reply([{ ...policy, id: "33333333-3333-4333-8333-333333333333", name: "New synthetic policy", edition: 2 }]) : reply([{ ...policy, state: "retired" }], policyId));
    vi.stubGlobal("fetch", fetchMock);
    const initial = { ...newDocumentRequirement("supporting"), file_policy_id: policyId, min_files: "0", max_files: "1", label_en: "Retained entered label" };
    render(<Harness initial={[initial]} />);
    expect(await screen.findByRole("option", { name: `Saved policy edition: ${policyId}` })).toBeTruthy();
    expect(screen.queryByRole("option", { name: "Synthetic policy · Edition 1" })).toBeNull();
    fireEvent.click(await screen.findByRole("button", { name: "Load more policy editions" }));
    await screen.findByRole("option", { name: "New synthetic policy · Edition 2" });
    fireEvent.change(screen.getByRole("textbox", { name: "English document label" }), { target: { value: "Keep local requirement" } });
    failure = true;
    fireEvent.click(screen.getByRole("button", { name: "Reload policy editions" }));
    await screen.findByText("Policy editions could not be loaded. Your entered requirements are preserved.");
    expect((screen.getByRole("textbox", { name: "English document label" }) as HTMLInputElement).value).toBe("Keep local requirement");
    expect(fetchMock.mock.calls[1][0]).toContain(`cursor=${policyId}`);
  });

  it("does not browse privileged policy APIs without the exact view permission and supports Tamil controls", async () => {
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    render(<Harness locale="ta" canView={false} initial={[newDocumentRequirement("optional")]} />);
    await waitFor(() => expect(fetchMock).not.toHaveBeenCalled());
    expect(screen.getByText(applicationDocumentWords.ta.policyDenied)).toBeTruthy();
    expect(screen.getByRole("button", { name: applicationDocumentWords.ta.add }).matches(":disabled")).toBe(true);
    expect(screen.getByRole("textbox", { name: applicationDocumentWords.ta.labelTa }).matches(":disabled")).toBe(true);
    expect(screen.getByRole("textbox", { name: applicationDocumentWords.ta.labelTa }).getAttribute("lang")).toBe("ta");
  });

  it("serializes zero as an explicit optional minimum and rejects omitted or inconsistent counts", () => {
    const value = { ...newDocumentRequirement("optional"), label_en: "Synthetic label", label_ta: "செயற்கைப் பெயர்", instructions_en: "Synthetic instructions", instructions_ta: "செயற்கை வழிமுறைகள்", file_policy_id: policyId, min_files: "0", max_files: "1" };
    expect(serializeDocumentRequirements([value])?.[0]).toMatchObject({ min_files: 0, max_files: 1 });
    for (const patch of [{ min_files: "" }, { max_files: "" }, { min_files: "2", max_files: "1" }, { min_files: "-1" }, { max_files: "101" }, { file_policy_id: "" }, { instructions_ta: " " }, { label_en: "" }]) {
      expect(serializeDocumentRequirements([{ ...value, ...patch }])).toBeNull();
    }
    expect(serializeDocumentRequirements([])).toEqual([]);
  });
});
