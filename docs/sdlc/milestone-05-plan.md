# Milestone 5 plan ? program delivery and participant portal

Status: P01.2 and P01.3 implemented locally; Milestone 5 remains in progress.

## P01.2 - enrollment conversion, participant projection, sessions and timeline

Scope: convert one finalized selected application into one organization-scoped Participant projection and Enrollment while retaining the existing Person; grant the existing account participant access; move the application to enrolled; emit audit, status history and a minimal-ID outbox event in the same transaction; administer bilingual cohort sessions; and expose an ownership-scoped participant schedule and lifecycle timeline.

Acceptance criteria:

1. Conversion requires `enrollment.manage`, an exact application version, selected state, a finalized selection cycle, an active cohort bound to the intake program, and available capacity.
2. One application creates at most one enrollment and one participant/cohort pair. Participant re-use is by `(organization, person)` and no identity/contact data is duplicated.
3. Participant, enrollment, enrolled application state/history, scoped Participant role binding, audit and `enrollment.created` outbox evidence commit atomically.
4. Program sessions require `schedule.manage`, a schedulable cohort, valid time range inside cohort dates, bilingual titles and mode/location consistency.
5. Participant status changes require `participant.update`, optimistic versions, allowed transitions and append-only reasoned history.
6. `participant.self` exposes only the authenticated Person's participant projection, enrollments, sessions and application/selection/enrollment/session timeline; staff-only reasons, scores and comments remain absent.
7. English/Tamil staff and participant web states, fixed BFF routes, applicant enrolled receipt, API contracts, migration rollback/drift, PostgreSQL tests, lint, types and production build satisfy the shared Definition of Done.

## P01.3 - center/cohort staff bindings

Scope: assign an active Training Center Coordinator account to one active center or one compatible non-terminal cohort; restrict coordinator reads and mutations to active assignments; and preserve reasoned assignment/revocation evidence.

Acceptance criteria:

1. Only staff.assignment.manage can create or revoke bindings. The target must be an active account with the Training Center Coordinator role in the same organization.
2. Center bindings cover every cohort at that center and permit new cohort creation there. Cohort bindings cover only the named cohort.
3. Coordinator catalog, cohort changes, participant status changes and session commands are filtered and authorized against the active binding; missing, foreign and revoked scopes are denied.
4. Active duplicates and center/cohort mismatches are rejected by service and PostgreSQL constraints. Assignment identity/scope is immutable, and the only mutation is an optimistic active-to-revoked command with timestamp and reasoned audit.
5. Program Managers, Directors and Super Admins retain organization-wide rights through their existing permissions. Coordinators do not receive program, intake or enrollment administration.
6. English/Tamil staff UI, fixed BFF routes, generated contracts, migration round-trip/drift, PostgreSQL/API tests, lint, types, build and browser acceptance satisfy the shared Definition of Done.

## Planned follow-ups

- A01.3 private documents after object storage, malware scanning and retention approval.
- L01 learning catalog and enrollment access based on P01.2 Enrollment.
- L03 attendance against ProgramSession and Enrollment.
