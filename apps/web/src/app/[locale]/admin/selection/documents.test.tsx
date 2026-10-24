import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import ReviewerDocuments from "./documents";
import { document, documentList, documentOrg, requirement } from "../../../../test-fixtures/application-documents";
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
const frozen = { ...document, usable: true, file: { ...document.file, state: "clean" as const, version: 7 }, submitted_evidence: { file_id: document.file.id, file_version: 5, sha256: document.file.sha256, byte_size: 3, frozen_at: "2026-10-23T09:00:00Z" } };
describe("assigned reviewer documents", () => {
  it("reads only on request and displays pinned bilingual labels and frozen byte evidence", async () => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json(documentList([frozen])));
    vi.stubGlobal("fetch", fetchMock);
    render(<ReviewerDocuments org={documentOrg} assignment={document.id} locale="ta" />);
    expect(fetchMock).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "ஒதுக்கப்பட்ட விண்ணப்ப ஆவணங்களைப் படி" }));
    await screen.findByRole("heading", { name: requirement.label_ta });
    expect(screen.getByText(/கோப்புப் பதிப்பு: 5/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "சரிபார்க்கப்பட்ட ஆவணத்தைப் பதிவிறக்கு" }).getAttribute("href")).toBe(`/api/selection/organizations/${documentOrg}/assignments/${document.id}/documents/${document.id}/content`);
    expect(screen.queryByRole("button", { name: /பதிவேற்று/ })).toBeNull();
  });
  it("removes stale download links when assignment access is revoked", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(Response.json(documentList([frozen]))).mockResolvedValueOnce(Response.json({ error: { code: "permission_denied" } }, { status: 403 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<ReviewerDocuments org={documentOrg} assignment={document.id} locale="en" />);
    fireEvent.click(screen.getByRole("button", { name: "Read assigned application documents" }));
    await screen.findByRole("link", { name: "Download verified document" });
    fireEvent.click(screen.getByRole("button", { name: "Refresh document status" }));
    await screen.findByText("Document information could not be loaded. Your application answers are preserved.");
    expect(screen.queryByRole("link", { name: "Download verified document" })).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
