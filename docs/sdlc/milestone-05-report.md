# Milestone 5 implementation report

Status: P01.2 implemented locally; milestone remains in progress.

## P01.2 enrollment conversion, participant projection, sessions and timeline

Migration `5c48c1c3e88b` adds Participant, Enrollment, ProgramSession, ParticipantStatusHistory and DomainOutbox. Composite foreign keys enforce organization/program/cohort boundaries. Application and status history now include enrolled; the submitted-evidence trigger permits only selected-to-enrolled while preserving application content. Participant history is append-only. Outbox identity/payload evidence is immutable while dispatch state remains updateable.

Conversion locks the selected application, checks optimistic version, finalized SelectionCycle, active bound cohort and capacity, then creates or reuses the organization/person Participant. It creates one Enrollment, grants the existing account the scoped Participant role, records application and participant history, audit and a minimal-ID `enrollment.created` outbox event in one commit. Unique application and participant/cohort constraints reject duplicates. No Person data is copied.

Program Directors, Program Managers and Super Admins receive participant view/update, enrollment manage and schedule manage. Participants receive system access plus self-only timeline permission. Training Center Coordinators remain read-only until a concrete center/cohort binding exists. Session creation validates cohort lifecycle, cohort date bounds, time order and delivery-mode location. The participant route resolves the authenticated user's Person and returns only their enrollment/session timeline.

Evidence: the A02.3 PostgreSQL workflow now continues through selected application conversion, duplicate rejection, participant role access, session scheduling, chronological timeline, immutable participant history and enrolled applicant receipt. Four focused selection/program tests pass. The program module passes strict MyPy and Ruff. Migration downgrade to A02.3, re-upgrade and Alembic drift checks pass. OpenAPI and TypeScript contracts were regenerated. Strict TypeScript, ESLint, 30 Vitest tests and the Next.js production build pass, including the new participant route.

Definition of Done: requirements and acceptance criteria are documented; migration constraints, indexes and rollback pass; transactional business rules and stable errors are implemented; authorization and owner scope are tested; audit/outbox payloads contain identifiers only; English/Tamil staff and participant web states are integrated; contracts and user/security/database/testing documentation are updated; lint, types, tests and build pass locally. Authenticated Chrome acceptance passes the full enrollment/session/timeline workflow with persisted database assertions, responsive layout and no JavaScript errors. Remote CI remains to be run before closing Milestone 5. Native runtime remains deferred under ADR 0004.
