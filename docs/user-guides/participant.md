# Account guide ? foundation

Choose Your account, then Create account. Supply name, email and a 12?128 character password. Verify email using the single-use code from the account message, then sign in. During local development only, the operator retrieves this message from the encrypted queue; no email is sent. The same account flow is available in Flutter. English/Tamil labels are provided.

Forgot password requests a reset message without revealing whether an email is registered. Reset password consumes its code and signs out all existing sessions. Account shows active devices; sign out one device or all devices. An expired/revoked session requires sign-in again. After a network failure, reconnect before assuming remote device revocation succeeded.

Program applications and the participant schedule are available after an approved enrollment; learning content remains pending. Do not submit real personal data or documents during foundation testing.

Public information: use Pages on web or the mobile home screen to browse published information in the selected language. Missing translations are unavailable; drafts and archived content are never shown. No sign-in is needed.


## Application draft

After signing in, choose an organization and open Application draft. A published form is required. Saving creates a new version and the completion indicator counts required fields. This development slice cannot submit an application or upload documents; do not enter real applicant data until the program fields, consent and retention policies are approved.

## Participant schedule

After staff converts a finalized selected application, sign in and open `/{language}/participant` for the organization. The page shows your application, selection and enrollment journey plus sessions for your enrolled cohorts in chronological order. Online sessions may omit a physical location; in-person and hybrid sessions include staff-provided joining details. You cannot see reviewer scores, comments or internal decision reasons.

## Complete lessons

Start an assigned course to enable its first eligible lessons. Locked lessons show that an earlier prerequisite remains. Mark each available lesson complete; the progress bar and course status update immediately. Completion is safe to retry. The course becomes completed automatically when its published rule is satisfied.

## Take a quiz

Start the assigned course and complete any prerequisite lesson shown for the quiz. Select one answer for every question and submit. The result and best percentage update immediately. A failed attempt can be retried while attempts remain. Passing the quiz or using the final attempt closes further submissions. Quiz status is separate from the current lesson-based course completion rule.

## Submit an assignment

Start the course and complete the assignment lesson's prerequisites. Enter the requested text response and submit it when ready. A submitted revision cannot be edited. Wait for trainer feedback before sending another revision; the page shows the score, pass state, feedback and remaining submissions. File attachments are not available in this release. Assignment results do not yet change the course completion percentage.

## Certificate eligibility and verification

The course shows separate lesson, quiz and assignment requirements. You become certificate-eligible after the course completion rule is met and every quiz and assignment has passing evidence. Authorized staff issue the certificate manually. When issued, your learning page shows its private details, QR code and verification link. The public verification page shows course, issuer, date and valid/revoked status but does not expose your name, scores, responses or feedback.

## Check in and review attendance

Open **My attendance** from the participant portal. Scan the QR shown by the trainer with a compatible app and paste its `edp-attendance:` value, or enter the provided check-in code. Check-in works only during the session window and only for your active enrollment. Repeating a successful check-in is rejected.

The page shows Present, Late, Absent, Excused, or Unmarked for each session and calculates your percentage. Present and Late count as attended; Excused sessions are removed from the counted total. A warning appears when the result is below the cohort threshold. Ask authorized staff to correct an error; the original record remains in the audit history. No location is collected.

## Draft and submit a business plan

Open **My business plan** from the participant portal for an active enrollment. Work through the 20 sections; each change saves after a short pause and creates a revision. Check the saved status before leaving. All sections must contain text before **Submit for mentor review** becomes available. Submission preserves a numbered snapshot. Your assigned mentor may approve it or request changes with comments. After a changes request, revise and submit again; earlier snapshots remain visible. Financial entries are planning assumptions, not guaranteed outcomes. PDF export is not yet available.

If another tab saves first, changes to different sections combine automatically. If both tabs change the same section, autosave pauses and **Review conflicting edits** shows the saved text alongside your edits. **Keep my edits** explicitly keeps your text for those sections and retries saving. **Load saved version** asks for confirmation before replacing your unsaved text. A further concurrent change can require another comparison.

After an interrupted save, use **Refresh saved plan**. The editor checks what was saved before retrying and keeps text you typed while the request was running. If the plan has been submitted or access is unavailable, it keeps your unsaved text visible without continuing to save. Wait for **Saved** before leaving; the editor warns on ordinary links, reload or tab close while edits remain unsaved. Keep the page open until recovery is complete, because plan text is not copied into persistent browser storage.

After a mentor requests changes, reload **My business plan** and expand the numbered **Submitted version** to read the review reason and section feedback. Edit the current plan, wait for **Saved**, and submit it again. The next submission receives a new number; the earlier submitted text and feedback remain available. After approval, the current plan is read-only and cannot be submitted again.

## Find resources and track funding

Open **Resources and funding** from the participant portal. Search schemes, funding programs and opportunities by kind, sector, geography, tag and availability. Check the official source, verification date, eligibility, required documents and opening/closing dates before acting. English and Tamil entries appear in their authored language. Public visitors can browse the public Resources page; participant-only entries require an active enrollment.

Use **Save resource** to keep an item and **Remove saved resource** to remove that preference. An archived or withdrawn resource appears as unavailable in saved items. Opportunity **Express interest** records your interest once; it does not send an application to the provider. Closed opportunities do not accept new expressions of interest.

For a funding program, choose **Start funding tracker**. Record progress with a short reason in this order: Interested, Eligibility check, Document preparation, Applied, Under review, then Approved or Rejected. Only Approved can progress to Disbursed. Rejected and Disbursed are final in this phase. Status and earlier reasons remain in **Progress history**; **Source recorded when tracking began** preserves the original program information. A closed program cannot start a new case, but existing case history remains available. If another tab changes the case, refresh progress before retrying. Avoid personal bank details, identity-document numbers or other unnecessary sensitive information in reasons.

Progress is your report of external activity. The platform does not submit an application, decide eligibility, approve funding or guarantee an outcome. Confirm decisions and current terms with the official provider.

## Get help and track business progress

Open **Helpdesk** from your participant schedule, choose a category and priority, describe the issue and create a ticket. You may attach up to three small plain-text `.txt` files (32 KiB each). Avoid passwords, identity numbers or banking details. The ticket number identifies your request. Shared replies and history appear in its details; internal staff notes remain private. Download files through their ticket links.

Reply when more information is requested. When staff resolve the ticket, close it if the issue is settled. To reopen a resolved or closed ticket, provide a reason; the request returns to the unassigned queue while retaining its history. **Ticket updates** shows in-app notices; mark them read or turn off future notices in this workspace. These are not email/SMS/push messages.

If a save is interrupted, keep your text and use the refresh action before another change. Ticket creation offers recovery of the original request without creating a duplicate. Business profiles and follow-up forms also keep input after errors: use **Refresh saved progress**, compare the saved version and then decide what to save. Each follow-up keeps its own draft. The scheduled dates remain fixed even if staff change the schedule for future profiles; early outcome reporting is allowed and does not move the date. Completed alumni retain access while their participant/enrollment status remains eligible. Public-listing interest does not make a business profile public.

## Record a business baseline and outcome

Open **My business outcomes** from your participant schedule. This form records minimal impact evidence even when you have no business profile. Select your enrollment and a published measurement definition, read the definition, choose Baseline or Outcome and the observation date, then record whether the business has started/is active and how many jobs were created. Enter a reason and save. These observations are self-reported; use the program's approved measurement instructions.

Observation history retains the edition and every revision. **Correct this observation** opens the latest saved version while fixing its original enrollment, date, stage and edition. Your correction adds evidence; it does not erase the earlier report. An edition archived after your original report can still identify a correction. After a stale change, refresh saved evidence and compare with your preserved fields before submitting. After an uncertain response, **Recover request** repeats the exact request without creating another observation. Do not put private financial or identity details in reasons.

Business-profile follow-up reports remain a separate workflow; they are not automatically copied into this evidence or added to its impact totals. Your enrollment/participant status must remain eligible to record evidence. Reporting staff see aggregates and coverage, not your private correction reason.
