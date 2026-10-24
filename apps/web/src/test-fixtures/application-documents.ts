import type { components } from "../lib/api-contracts";
export const documentOrg = "11111111-1111-4111-8111-111111111111";
export const documentApplication = "22222222-2222-4222-8222-222222222222";
export const requirement: components["schemas"]["DocumentRequirementView"] = {
  id: "33333333-3333-4333-8333-333333333333", key: "synthetic_evidence", label_en: "Synthetic evidence", label_ta: "செயற்கைச் சான்று",
  instructions_en: "Synthetic instructions only", instructions_ta: "செயற்கை வழிமுறைகள் மட்டும்", min_files: 1, max_files: 1, position: 1,
  file_policy_id: "44444444-4444-4444-8444-444444444444", file_policy: { id: "44444444-4444-4444-8444-444444444444", edition: 1, name: "Synthetic file rules", notice_en: "Synthetic notice only", notice_ta: "செயற்கை அறிவிப்பு மட்டும்", allowed_mime_types: ["application/pdf"], max_file_bytes: 4096, max_upload_bytes: 1024, max_files: 2, retention_days: 30, rejected_retention_days: 3, allow_frozen_disposal: false },
};
export const document: components["schemas"]["ApplicationDocumentView"] = {
  id: "55555555-5555-4555-8555-555555555555", requirement_id: requirement.id, usable: false, removed_at: null, replaced_by_id: null, submitted_evidence: null,
  file: { id: "66666666-6666-4666-8666-666666666666", organization_id: documentOrg, owner_person_id: "77777777-7777-4777-8777-777777777777", purpose: "application_document", resource_id: "55555555-5555-4555-8555-555555555555", policy_id: requirement.file_policy_id, client_request_id: "88888888-8888-4888-8888-888888888888", media_type: "application/pdf", byte_size: 3, sha256: "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", state: "pending", version: 1, verified_at: null, scanned_at: null, scan_attempts: 0, failure_code: null, retention_until: "2026-11-22T08:00:00Z", legal_hold: false, evidence_frozen: false, deleted_at: null, created_at: "2026-10-23T08:00:00Z", updated_at: "2026-10-23T08:00:00Z" },
};
export const documentList = (items: components["schemas"]["ApplicationDocumentView"][] = [], overrides: Partial<components["schemas"]["ApplicationDocumentList"]> = {}): components["schemas"]["ApplicationDocumentList"] => ({ application_id: documentApplication, application_version: 1, collection_enabled: true, max_upload_bytes: 1024, document_requirements: [requirement], items, next_cursor: null, ...overrides });
