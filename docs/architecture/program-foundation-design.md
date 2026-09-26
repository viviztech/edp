# Program delivery foundation design

Status: P01.1, P01.2 and P01.3 implemented. Authority: master Sections 9, 10, 19, 21, 30, 36 and 37.

## Domain boundary

Program is the organization-owned offering. TrainingCenter is an organization-owned delivery location. Cohort binds one active Program to one active TrainingCenter with dates and optional capacity. ApplicationCycle binds an active Program, optional compatible non-terminal Cohort and one immutable published ApplicationForm to an intake window.

P01.2 implements ProgramSession, Participant and Enrollment. Enrollment is created only by the selected-application conversion transaction, retaining Person and Application links, unique application/cohort membership, audit and outbox evidence atomically. ProgramCalendar remains a projection of ProgramSession.

## Integrity and lifecycle

Every domain row includes an optimistic version. Composite foreign keys include organization_id, and the cycle-to-cohort key also includes program_id. This makes tenant and program mismatches invalid even if service checks are bypassed.

Allowed transitions are Program draft to active to archived; TrainingCenter active to inactive or inactive to active; Cohort planned to active or cancelled, and active to completed or cancelled; ApplicationCycle draft to open or cancelled, and open to closed or cancelled. Terminal states cannot reopen. State commands require expected_version and a bounded reason, and audit actor, organization, resource, request ID, new version and changed field names without copying bilingual names or form content.

## Authorization and API

The organization-scoped permissions are program.view, program.manage, cohort.manage and application.cycle.manage. Program Directors, Program Managers and Super Admins receive all four. Training Center Coordinators receive program view plus cohort, participant and schedule permissions only when a current ProgramStaffAssignment limits them to a center or cohort. Program Managers, Directors and Super Admins remain organization-wide. Assignment administration uses a separate staff.assignment.manage permission.

Endpoints are under /api/v1/programs/organizations/{organization}. GET /catalog returns bounded lists. POST creates a resource, PATCH edits mutable fields, and POST /{resource}/{id}/state performs an explicit lifecycle command. The Next.js route /{locale}/admin/programs uses a dedicated allowlisted proxy with session forwarding, same-origin CSRF validation, a 64 KiB JSON body limit, no-store responses and noindex metadata.

## Operations and rollback

Apply migrations through 6d59d2d4f99c and rerun the idempotent identity role seed before opening the workspace. A schema downgrade is limited to disposable databases because it drops program delivery data and the application-form composite scope constraint. Production rollback should keep the schema and disable the route while preserving audit and domain records.


## P01.3 scoped staff binding

ProgramStaffAssignment is authorization evidence, not copied profile data. It references the existing User and one TrainingCenter, with an optional Cohort that must belong to the same center and organization. A center-level row authorizes all current and later cohorts at that center; a cohort-level row authorizes only that cohort. Active bindings are unique per user/scope. Revocation is retained as immutable history, and services resolve permissions plus the active binding for every coordinator request.
