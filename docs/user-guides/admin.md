# Administrator guide ? foundation

An operator provisions an account and exact organization role using the documented CLI; no shared default credentials. Sign in through /en/account or /ta/account. Your organizations lists only current authorized workspaces. Open a workspace to view its name; Audit history is available only with audit.view. Unauthorized or revoked grants are rejected by the backend even if a link is retained.

Account lists current devices and supports per-device, current-device and all-device sign-out. Password reset invalidates every session. In development, verification/reset messages are available through trusted operator CLI, not real email. The workflows below support local acceptance; production release gates remain open. Use synthetic data only until those gates pass.

CMS: open Publishing workspace from the staff page. Choose an organization and page, or create a page with a permanent lowercase address. Select content language, enter title/plain-text body and optional search metadata, then Save draft. Preview shows the saved draft. Publish saved draft updates only that language. Editing does not change published content. Archive requires a reason; restore keeps content as an unpublished draft. Publication history is read-only. A conflict means another edit occurred: select the page again to load current values before reconciling.

## Public enquiries

Open **Enquiry inbox** in the intended organization. The list can show New, Reviewed, Closed or all statuses; use **Load more** for later records. Select an enquiry to read its contact details, question and recorded consent version. Authorized managers can mark New as Reviewed, then close a reviewed enquiry. Received contact details and questions cannot be edited. There is no internal-note or outbound-response control in this workspace.

If a change conflicts or its response is interrupted, use the detail **Refresh** action and check the saved status before continuing. The controls stay paused until current details are loaded. Do not repeat a status command automatically. Access is limited to the organization's enquiry permissions; retain contact data only according to the approved operational policy.

The public form is disabled by default. Before collecting real enquiries, the owner must approve both language versions of the notice and consent wording, retention and response arrangements. An operator configures the approved notice URLs and consent texts with `CONTACT_PRIVACY_NOTICE_URL_EN/TA`, `CONTACT_CONSENT_TEXT_EN/TA`, the current `CONTACT_PRIVACY_VERSION`, and `CONTACT_ENQUIRIES_ENABLED`. Both languages are required before enabling. See [enquiry configuration and boundaries](../architecture/enquiry-web-journey.md). Local automated acceptance uses synthetic policy wording only.

## News, events, FAQs and testimonials

Open **Content studio** in the intended organization. Select the content type and language, then create a separate locale draft using the same permanent slug as its counterpart. Save and review the draft before publishing. Creation, editing, publication and archiving each require their own permission. Published entries must be archived with a reason and restored to draft before editing; archiving removes the entry from public discovery immediately. Republish the reviewed draft when ready.

Unsaved changes block switching to another entry. On a version conflict, keep the entered draft, load the latest saved values, compare them, then explicitly choose the latest version while retaining the intended changes before saving. Never replay a stale publication command without checking the current state.

**Media records** shows only recorded filename/type/size, scan state and visibility for staff with media-view permission. It does not offer secure uploads, downloads or publication. Those operations await the shared secure-file development process; metadata is not proof that file bytes have been stored or scanned.

CRM assignment notices: staff with crm.lead.view can open /{locale}/admin/notifications, choose their organization, and view their own in-app notices. A new notice appears after the background worker handles an assignment to them, provided their grant, active account, ownership and preference still allow it. Mark a notice read to acknowledge it. Turn assignment notices off or on using the preference control; changes affect pending and future notices, while already delivered notices remain. The CRM link opens the scoped lead queue for follow-up. A conflict means the item or preference changed; reload before trying again.


Follow-up reminders: an incomplete CRM call, email, meeting or task with a due time can produce an in-app reminder for the lead's current assignee after the background scheduler runs. The Notifications page has separate controls for assignment notices and follow-up reminders. Turn either off to stop its pending and future notices. Completed or reassigned follow-ups are rechecked before delivery. Use the CRM queue link to review the actual work; reminder text does not include the lead's details.

Selection: configure and publish a rubric, activate the selection cycle after intake closure, assign reviewers and wait for cleared conflicts and submitted scores. Use Application score aggregates to shortlist an evidence-backed application. Schedule its interview with start/end, mode and one or more panel members. Each panel member submits their score once; after all have submitted, complete the interview. A Director or Super Admin can select, waitlist or reject, and can override a terminal result only with a recorded reason. Finalize the cycle after every assigned application has a terminal result. Scores and internal comments are never applicant-visible, and enrollment is completed later through the participant/enrollment workflow.

## Enrollment and program schedule

After a selection cycle is finalized, open Programs. Selected applicants with a cohort appear under enrollment candidates. Create enrollment only after confirming cohort capacity; the action creates the participant link and changes the applicant receipt to enrolled. Use Participants for reasoned suspend/reactivate/complete transitions. Create bilingual sessions within cohort dates and provide a location for in-person or hybrid delivery. Complete or cancel sessions with a reason.


## Center and cohort coordinators

Provision the staff account and grant Training Center Coordinator in the correct organization before assigning delivery scope. In Programs, use Center and cohort staff assignments, enter the exact account email, choose an active center and optionally one of its planned or active cohorts, then record the assignment reason. Leaving cohort blank grants every cohort at that center, including later cohorts. Selecting a cohort grants only that cohort. Revoke an assignment with a reason as soon as responsibility ends; the coordinator loses scoped catalog and mutation access on the next request. Use a new assignment instead of editing retained scope evidence.

## Learning course studio

Open Learning from the staff workspace. Create a bilingual course, then add modules and lessons in their intended positive-number order. Add only private provider references; do not paste public credentials or real participant data. Publication freezes the structure, requires every module to contain a lesson, and records the approval reason. After publication, add the course to a planned or active cohort at a unique pathway position.

Participants with an active enrollment open My learning path. They see only published courses assigned to their enrolled cohorts and can start each course once; repeated start requests return the same record. Private material labels are visible, while the provider reference and download URL remain hidden until the approved media service is configured.

## Configure course completion

In Learning, create all modules and lessons in their final order. Add a prerequisite only from an earlier lesson to a later lesson. Choose Complete every lesson or set a positive minimum lesson count, record the reason, and publish only after review. Published rules and prerequisites cannot be edited. The cohort pathway shows assigned, started, completed, and average progress counts.

## Configure a quiz

Before publishing a course, open Learning and add a quiz to a lesson. Set its bilingual title and instructions, pass mark, maximum attempts and order. Add each bilingual question with points, then add at least two choices and mark exactly one as correct. Review the answer key before publication because the published quiz cannot be edited. Publication is blocked when a quiz has no questions or a question has an incomplete answer key.

## Configure an assignment

Before publishing a course, add an assignment to its lesson. Enter the bilingual title and instructions, maximum and passing points, order, and the number of allowed submissions. Review these settings before publication because the definition is frozen with the course. This release accepts text responses only; do not request files or sensitive personal evidence in the instructions.

## Publish and issue certificates

After publishing the course, create its bilingual certificate template with a unique code, statement and approved issuer name. Program Managers may prepare the draft; a Program Director or Super Admin must publish it with a reason. Only one template can be published for a course.

The Certificate eligibility section recalculates lesson completion and passed quiz/assignment counts. Issue only when it shows eligible and record the operational reason. Issuance is manual because attendance thresholds and signatories are not approved. A certificate cannot be edited. If it must no longer verify as valid, revoke it with the exact reason; the public verification page will show revoked without disclosing the learner's identity.

## Manage attendance

Open **Attendance** after program sessions and delivery staff assignments exist. Save the cohort policy before opening check-in. Confirm the threshold, late boundary, opening offset, and closing offset with the program owner and record the approval reason.

For a scheduled session, open its QR window and immediately show the generated QR to enrolled participants; the raw token is displayed only during that browser session. Close the window as soon as check-in finishes. Mark any remaining participant as Present, Absent, Late, or Excused. An existing mark must be changed through **Correct** with the exact reason; corrections retain the prior value and actor. Never enter medical details in the reason. The platform does not collect participant location.

## Review assigned business plans

Open **Business plan reviews** from Mentoring. Only an active mentor assignment grants access to a participant's submitted snapshot. Read the submitted version, add section comments where useful, enter a review reason, and choose **Request changes** or **Approve**. A review is recorded once for that submission and cannot be edited. A participant can submit a new version after a changes request. Draft changes made after a review are not part of an earlier submitted snapshot.

Check the enrollment and numbered submission before recording a decision. Only the latest submitted version offers a review form. The form pauses while the decision is being recorded. If a request fails or another tab has already reviewed the submission, your entered feedback stays visible; use **Refresh assigned plans** before retrying. If the earlier request was saved, the recorded feedback appears without submitting it again. A saved review remains recorded even if refreshing the list fails.

If an assignment ends or a newer submission arrives, earlier entered feedback stays visible in a disabled form. It is never copied automatically to a different submission. Open the latest submission and review its actual evidence. Earlier numbered snapshots and recorded reviews remain unchanged after participant revisions and approval.

## Publish schemes, funding and opportunities

Open **Resources and funding** in the correct organization. Create a Scheme, Funding or Opportunity entry in English or Tamil, with provider, type, eligibility, benefits, sector, geography, process, document labels, official source and last verification date. Add dates, contact information and tags as applicable. Enter a funding amount only when the official source supplies it. English and Tamil editions are authored separately; changing the interface language selects that language's resource list.

Save the draft, review its content, enter a reason and publish it for Public or Participants visibility. Published content must return to draft before editing; it disappears from discovery until republished. Archive entries that should no longer be offered. Each change requires the loaded version and preserves its prior evidence. A conflict means another change was saved: refresh the saved resource, compare it with your entered text and decide what to save. Check the saved result before leaving.

Public visitors see published public entries. Actively enrolled participants can also see published participant entries. Closing dates derive the Closed label; existing funding cases retain their original source and history after expiry, editing or archival. Funding staff can read their organization's funding-progress queue, but cannot change a participant's status on their behalf. The tracker records external, self-reported progress and does not award or guarantee funding. Verify current conditions with the official provider and follow the organization's approved content-review process.

## Operate the helpdesk and post-training follow-ups

Open **Helpdesk** in the selected organization. **Assigned tickets** contains your current work. **Unassigned tickets** exposes minimal category/priority/number information: enter an assignment reason and claim a ticket to see its discussion. Organization administrators can review the organization queue and route work to an eligible active staff user. Handing over removes the previous assignee's future access.

Move Assigned to In progress, then request information with Waiting for user or resolve the issue. An owner reply resumes work. Resolve before closing; only the owner or organization admin can reopen, with a reason, returning the ticket to the claim queue. Priority changes also need a reason. **Internal note** keeps the message and any attached text files staff-only. Shared replies/status changes create minimal owner notices; assignments and owner replies create assignee notices. Internal notes never notify the participant. There is no promised SLA or outbound provider delivery.

On stale/interrupted changes, refresh and compare before retrying. Keep unnecessary personal or financial details out of notes, files and reasons. The business follow-up schedule applies to new profiles only; existing dates stay frozen. Use **Refresh saved schedule** after a conflict; your proposed offsets and reason remain available. Staff summaries show submitted/due counts, while only the owner can submit an outcome.

## Reporting, measurement definitions and exports

Open **Reports and impact** in the intended organization. Select inclusive UTC dates, a program/cohort where needed, and apply filters. Each measure offers its definition, source, time basis, numerator/denominator and caveat. Current statuses are observed when generated; they do not reconstruct a historical status at the period end. An unavailable value is not zero. Lead attribution is unavailable under program/cohort filters when the source has no reliable assignment. Funding transaction amounts are not recorded, so the platform makes no funding-facilitated amount claim.

Measurement managers create a bilingual definition edition from approved instructions and explicitly publish it with a reason. Its structured measures are business started, business active and jobs created. Participants retain the edition used when reporting; archive superseded editions instead of rewriting them. Impact coverage states how many scoped enrollments reported evidence. The reporting population includes withdrawn enrollments recorded by the end date, preserving historical evidence. Mixed editions are grouped separately, and a jobs-change comparison uses only matching baseline/outcome samples within the same edition. B02 business-profile outcomes are a separate source. Counts and changes do not establish verified or causal impact.

**Create snapshot of applied filters** saves a freshly generated coherent report and its definitions. Later source corrections cannot change it. Select a snapshot to review or compare periods/populations, keeping the displayed context in mind. Export-enabled directors can enter a reason and create an aggregate CSV from the selected snapshot. Program Managers and view-only staff cannot export without a separate grant. Download within the job's expiry; a fresh short-lived authorized access capability is issued for each download. CSV contains aggregate evidence and context, not participant lists. Failed or interrupted creation offers exact request recovery. Avoid using a difference between distinct populations as a causal result.
