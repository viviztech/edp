# L03 attendance and QR check-in design

Status: implemented locally; release gates remain in the Milestone 6 report.

Attendance is a separate domain boundary over the existing `ProgramSession`, `Cohort`, `Enrollment`, `Participant`, and `ProgramStaffAssignment` records. It does not copy participant identity, session scheduling, or delivery scope.

## Policy and calculation

Each cohort may have one optimistic-versioned `AttendancePolicy`. It defines the low-attendance threshold, late boundary, and QR opening/closing offsets. Until an approved policy is saved, the learner projection uses a 75% display threshold and staff cannot open a QR window. The service counts a non-cancelled session after it starts or is completed. `present` and `late` count as attended; `excused` is removed from the denominator; an unmarked elapsed session counts as missed. Percentages and low-attendance state are derived and cannot be supplied by a client.

## Evidence and corrections

`AttendanceRecord` is unique by session and enrollment. Manual and QR commands both derive session/cohort/enrollment scope on the server. A duplicate command is rejected rather than overwriting evidence. Corrections require the exact record version, a changed status, and a bounded reason. The current record advances one version while an immutable `AttendanceCorrection` preserves actor, previous status, new status, version, reason, and timestamp. PostgreSQL triggers reject record deletion, identifier/source rewrites, unversioned updates, and correction mutation.

## QR security

Opening a window generates 256 bits of random token material. Only its SHA-256 digest is stored. The raw token is returned once to the authorized staff browser and is absent from audit details and normal workspace reads. A window is bound to one session, has a database-enforced time range, and only one active window may exist per session. Check-in requires an authenticated participant with an active enrollment in that session's cohort, an exact token digest, an active window, current time inside the window, and an unmarked attendance row. The server derives `present` or `late`. Closing a window is explicit and versioned.

The QR contains only `edp-attendance:<opaque token>`. It contains no person, enrollment, session, organization, or location data. Precise location is neither accepted nor stored. A future location policy requires a separate approved design and privacy review.

## Authorization and clients

Program Directors, Program Managers, and Super Admins have organization-wide `attendance.view` and `attendance.manage`. Trainers and Training Center Coordinators also have both permissions but require an active center/cohort `ProgramStaffAssignment`; revocation applies on the next request. Participants use `participant.self`, and the service derives their enrollment from the authenticated Person.

Next.js exposes fixed allowlisted BFF paths, same-origin CSRF checks for mutations, a staff register/policy/QR workspace, and a participant check-in/history view in English and Tamil. Native Flutter remains deferred under ADR 0004.
