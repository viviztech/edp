# Milestone 5 plan ? program delivery and participant portal

Status: P01.2 implemented locally; Milestone 5 remains in progress.

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

## Planned follow-ups

- A01.3 private documents after object storage, malware scanning and retention approval.
- P01.3 center/cohort staff bindings before Training Center Coordinators receive mutation permissions.
- L01 learning catalog and enrollment access based on P01.2 Enrollment.
- L03 attendance against ProgramSession and Enrollment.
