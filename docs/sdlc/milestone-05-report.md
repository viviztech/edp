# Milestone 5 implementation report

Status: P01.2 and P01.3 implemented locally; milestone remains in progress.

## P01.2 enrollment conversion, participant projection, sessions and timeline

Migration `5c48c1c3e88b` adds Participant, Enrollment, ProgramSession, ParticipantStatusHistory and DomainOutbox. Composite foreign keys enforce organization/program/cohort boundaries. Application and status history now include enrolled; the submitted-evidence trigger permits only selected-to-enrolled while preserving application content. Participant history is append-only. Outbox identity/payload evidence is immutable while dispatch state remains updateable.

Conversion locks the selected application, checks optimistic version, finalized SelectionCycle, active bound cohort and capacity, then creates or reuses the organization/person Participant. It creates one Enrollment, grants the existing account the scoped Participant role, records application and participant history, audit and a minimal-ID `enrollment.created` outbox event in one commit. Unique application and participant/cohort constraints reject duplicates. No Person data is copied.

Program Directors, Program Managers and Super Admins receive participant view/update, enrollment manage and schedule manage. Participants receive system access plus self-only timeline permission. At the P01.2 checkpoint, Training Center Coordinators remained read-only pending a concrete center/cohort binding; P01.3 below supersedes that limitation. Session creation validates cohort lifecycle, cohort date bounds, time order and delivery-mode location. The participant route resolves the authenticated user's Person and returns only their enrollment/session timeline.

Evidence: the A02.3 PostgreSQL workflow now continues through selected application conversion, duplicate rejection, participant role access, session scheduling, chronological timeline, immutable participant history and enrolled applicant receipt. Four focused selection/program tests pass. The program module passes strict MyPy and Ruff. Migration downgrade to A02.3, re-upgrade and Alembic drift checks pass. OpenAPI and TypeScript contracts were regenerated. Strict TypeScript, ESLint, 30 Vitest tests and the Next.js production build pass, including the new participant route.

Definition of Done: requirements and acceptance criteria are documented; migration constraints, indexes and rollback pass; transactional business rules and stable errors are implemented; authorization and owner scope are tested; audit/outbox payloads contain identifiers only; English/Tamil staff and participant web states are integrated; contracts and user/security/database/testing documentation are updated; lint, types, tests and build pass locally. Authenticated Chrome acceptance passes the full enrollment/session/timeline workflow with persisted database assertions, responsive layout and no JavaScript errors. Remote CI remains to be run before closing Milestone 5. Native runtime remains deferred under ADR 0004.


## P01.3 center/cohort staff bindings

Migration 6d59d2d4f99c adds ProgramStaffAssignment with organization, user, center and optional cohort scope. Composite foreign keys require a cohort assignment to match its center and organization. Partial unique indexes prevent duplicate active center and cohort bindings. PostgreSQL permits only the versioned active-to-revoked transition and rejects identity/scope edits and deletes.

Program Managers, Program Directors and Super Admins receive staff.assignment.manage. Training Center Coordinators receive cohort, participant and schedule permissions, but each read and mutation also resolves an active center/cohort assignment. A center assignment permits cohort creation and covers all cohorts at that center; a cohort assignment covers only that cohort. Catalog results, sessions, enrollments and participants are filtered before serialization. Coordinators never receive program, application-cycle or enrollment administration.

The English/Tamil Programs workspace creates center/cohort assignments by an existing coordinator account email, lists versioned scope and revokes with a reason through exact CSRF-protected BFF paths. Audit rows contain identifiers, changed field names and the operator reason without copying participant or session data.

Evidence: focused PostgreSQL/API coverage passes unassigned denial, assignment-role validation, duplicate protection, scoped catalog visibility, allowed and denied session mutation, direct database tamper rejection, audited revocation and HTTP routes. The complete PostgreSQL-backed API suite passes 83 tests. Migration downgrade/re-upgrade and Alembic drift pass. OpenAPI and TypeScript contracts were regenerated; focused strict MyPy and Ruff pass. Strict TypeScript, ESLint, 30 Vitest tests and the Next.js production build pass. Authenticated Chrome creates and revokes a center assignment, verifies filtered coordinator records, permits an assigned session, rejects an unassigned cohort request, proves immediate access removal, checks persisted evidence and mobile overflow, and reports no JavaScript errors.

Definition of Done: requirements, migration constraints and rollback, service rules, stable errors, scoped authorization, immutable evidence, audit, English/Tamil UI, API contracts, PostgreSQL/API/web/browser tests, lint, types and production build pass locally. Remote CI remains unverified, and Milestone 5 stays open for later delivery slices and release gates.
