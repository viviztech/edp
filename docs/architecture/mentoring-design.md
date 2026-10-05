# M01 mentoring design

Status: M01 implemented locally.

## Boundary and lifecycle

Mentoring owns mentor profiles, expertise, recurring availability, enrollment-scoped assignments, sessions, notes, goals, action items, follow-up reminders and participant feedback. Programs remains the source of participants, enrollments and programs; Identity remains the source of users, roles, permissions and audit evidence.

An active mentor profile may be assigned to one active Enrollment. The database permits one active mentor assignment per enrollment while preserving ended assignments. A scheduled session must fall inside the assignment dates and cannot overlap another scheduled session for the same mentor. Sessions transition once from scheduled to completed or cancelled. Ending an assignment is versioned and reasoned.

## Authorization and privacy

- Super Admin, Program Director and Program Manager hold `mentoring.admin`, `mentoring.manage` and `mentoring.view` across their organization grant.
- Mentor holds `mentoring.manage` and `mentoring.view`; every command and projection is restricted to assignments linked to that mentor's profile.
- Participant receives only their own assignment through User -> Person -> Participant -> Enrollment. Caller-provided participant identifiers never establish ownership.

Notes are append-only. `mentor_private` content is returned only to its author, including in the administration workspace. Administration receives session, goal, reminder and feedback aggregates without another mentor's private note body. `shared_with_participant` notes appear in the participant projection. PostgreSQL rejects update or deletion of notes and feedback.

## Outcomes and reminders

Goals carry versioned progress and terminal completed/cancelled states. Action items may attach to a goal and transition once from open to completed or cancelled. Follow-up records are durable reminders with a due time, derived overdue state and versioned completion/cancellation. They remain inside the mentoring boundary because the current notification intent schema is CRM-specific; a later N01 extension may dispatch these records without changing M01 ownership.

Participant feedback is accepted once per completed session, rated from one to five, and stored as immutable evidence. Mentor/admin monitoring exposes count and average rating. It does not expose participant identity beyond the already assigned relationship.

## Interfaces and deferred channels

The FastAPI module exposes organization-scoped staff and participant workspaces plus explicit commands. The Next.js BFF uses a closed route allowlist, browser session forwarding, origin-bound CSRF validation, JSON-only mutations, request limits and no-store responses. English and Tamil web routes cover the staff and participant journeys.

Native mentor access remains deferred under ADR 0004 until the macOS stage. Production reminder delivery, retention approval, calendar integration and native-device acceptance remain release gates rather than M01 functional defects.
