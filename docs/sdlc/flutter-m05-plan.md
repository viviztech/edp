# Flutter M05 alumni, impact and enrollment updates

Prepared: 2026-10-24 (Asia/Calcutta). This refines the authorized M05 portion of the Flutter domain plan. All work remains local with synthetic acceptance data; deployment, providers, production collection and native execution remain separate gates.

Implement typed owner-only business entries, bounded private profile create/update fields, immutable revisions, server-provided follow-up due dates and one immutable outcome per follow-up. Preserve form input on errors. Creation/update/outcome writes are sent once, followed by an explicit owner readback after uncertainty or conflict; a returned existing profile never authorizes overwrite.

Implement separate self-reported impact observations using eligible enrollments and published definitions from the existing API. Keep enrollment/definition/record cursors independent, pin definition ID/edition and date/stage, and preserve one unchanged request UUID/body while uncertain. Revisions require a reason and expected revision; authoritative readback precedes explicit retry.

Implement participant enrollment inbox pagination, versioned read status and notification preference. Resolve only the documented schedule action, re-read current inbox visibility and verify the notice's enrollment in the owned timeline before routing. No arbitrary URL, CRM inbox access or push delivery is introduced.

Acceptance includes active/completed owner access, peer/organization denial, profile conflict/revisions, fixed schedules, invalid future dates/flags, immutable outcomes, impact definition/revision/idempotency rules, independent pagination, input preservation, session/context disposal, English/Tamil narrow layouts and guarded real PostgreSQL/API checks. Tests use in-memory tokens only within fixtures. Document actual results and retain native/provider/release deferrals explicitly.
