# Administrator guide ? foundation

An operator provisions an account and exact organization role using the documented CLI; no shared default credentials. Sign in through /en/account or /ta/account. Your organizations lists only current authorized workspaces. Open a workspace to view its name; Audit history is available only with audit.view. Unauthorized or revoked grants are rejected by the backend even if a link is retained.

Account lists current devices and supports per-device, current-device and all-device sign-out. Password reset invalidates every session. In development, verification/reset messages are available through trusted operator CLI, not real email. Publishing/CRM/selection workflows are not yet released. Use synthetic data only until production gates pass.

CMS: open Publishing workspace from the staff page. Choose an organization and page, or create a page with a permanent lowercase address. Select content language, enter title/plain-text body and optional search metadata, then Save draft. Preview shows the saved draft. Publish saved draft updates only that language. Editing does not change published content. Archive requires a reason; restore keeps content as an unpublished draft. Publication history is read-only. A conflict means another edit occurred: select the page again to load current values before reconciling.

CRM assignment notices: staff with crm.lead.view can open /{locale}/admin/notifications, choose their organization, and view their own in-app notices. A new notice appears after the background worker handles an assignment to them, provided their grant, active account, ownership and preference still allow it. Mark a notice read to acknowledge it. Turn assignment notices off or on using the preference control; changes affect pending and future notices, while already delivered notices remain. The CRM link opens the scoped lead queue for follow-up. A conflict means the item or preference changed; reload before trying again.


Follow-up reminders: an incomplete CRM call, email, meeting or task with a due time can produce an in-app reminder for the lead's current assignee after the background scheduler runs. The Notifications page has separate controls for assignment notices and follow-up reminders. Turn either off to stop its pending and future notices. Completed or reassigned follow-ups are rechecked before delivery. Use the CRM queue link to review the actual work; reminder text does not include the lead's details.

Selection: configure and publish a rubric, activate the selection cycle after intake closure, assign reviewers and wait for cleared conflicts and submitted scores. Use Application score aggregates to shortlist an evidence-backed application. Schedule its interview with start/end, mode and one or more panel members. Each panel member submits their score once; after all have submitted, complete the interview. A Director or Super Admin can select, waitlist or reject, and can override a terminal result only with a recorded reason. Finalize the cycle after every assigned application has a terminal result. Scores and internal comments are never applicant-visible, and enrollment is completed later through the participant/enrollment workflow.

## Enrollment and program schedule

After a selection cycle is finalized, open Programs. Selected applicants with a cohort appear under enrollment candidates. Create enrollment only after confirming cohort capacity; the action creates the participant link and changes the applicant receipt to enrolled. Use Participants for reasoned suspend/reactivate/complete transitions. Create bilingual sessions within cohort dates and provide a location for in-person or hybrid delivery. Complete or cancel sessions with a reason.


## Center and cohort coordinators

Provision the staff account and grant Training Center Coordinator in the correct organization before assigning delivery scope. In Programs, use Center and cohort staff assignments, enter the exact account email, choose an active center and optionally one of its planned or active cohorts, then record the assignment reason. Leaving cohort blank grants every cohort at that center, including later cohorts. Selecting a cohort grants only that cohort. Revoke an assignment with a reason as soon as responsibility ends; the coordinator loses scoped catalog and mutation access on the next request. Use a new assignment instead of editing retained scope evidence.
