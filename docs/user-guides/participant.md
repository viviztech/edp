# Account guide ? foundation

Choose Your account, then Create account. Supply name, email and a 12?128 character password. Verify email using the single-use code from the account message, then sign in. During local development only, the operator retrieves this message from the encrypted queue; no email is sent. The same account flow is available in Flutter. English/Tamil labels are provided.

Forgot password requests a reset message without revealing whether an email is registered. Reset password consumes its code and signs out all existing sessions. Account shows active devices; sign out one device or all devices. An expired/revoked session requires sign-in again. After a network failure, reconnect before assuming remote device revocation succeeded.

Program applications are available before enrollment. Participant services become available according to your current organization permissions and enrollment. Account links preserve the selected organization and language. Use synthetic information during local acceptance. Application document controls appear only for configured requirements when the organization's file service is enabled.

Public information: use Pages on web or the mobile home screen to browse published information in the selected language. Missing translations are unavailable; drafts and archived content are never shown. No sign-in is needed.


## Account codes and program updates

An approved account email contains a code and a fixed Verify email or Reset password page. Open the page and enter the code explicitly; opening a link alone never changes an account. The code applies to its own account even if another account is currently signed in. Successful submission clears the code/password. Development uses an operator-retrieved synthetic message and sends no email.

After enrollment, open My updates in your organization navigation. Your enrollment update links to the current program schedule. Mark as read preserves the update until expiry. Update preferences controls future in-app enrollment updates only; it does not change email/other channels or restore previously suppressed updates. If a save is uncertain, check its current state before explicitly retrying. Revoked program access hides the corresponding notices.

## Apply and track an application

Choose **Apply** from the public website, or open applications from your account. Registration, verification and sign-in preserve a valid chosen organization/intake. An ordinary applicant does not need a staff role. Choose an open intake, start its application and save your draft. Complete the required fields, review the declarations/consents and submit explicitly when ready. Submission records an application number and freezes the submitted answers.

**Saved and submitted applications** lists your own records independently of currently open intakes. Use its continuation controls to see later records, continue an available draft or view a submitted receipt and status history. Intake closure does not remove your earlier application; a closed draft is read-only. Scores, reviewer comments and internal decision reasons are never shown. If a chosen intake is unavailable, the page does not silently substitute a different application. Refresh and check the selected record after an interrupted or stale request before continuing.

## Attach application documents

The application shows its own document labels, instructions, notice, allowed formats, file counts and current upload limit. Follow those configured requirements; the platform does not assume a required document list. An unavailable collection notice means files cannot currently be uploaded. Save your application answers before changing documents. Draft saving does not require accepting the final declarations yet.

Choose **Upload document**, select the file and explicitly upload it. Keep the page open while it is registered and verified. **Recover the same document registration** recovers an interrupted registration without creating a duplicate. **Read current document** checks an interrupted upload before another command; the page never resends bytes automatically. Continue a registered upload only through its explicit continuation control.

Files awaiting scanning, rejected or unsafe files, and files unavailable under retention rules cannot satisfy submission. Refresh document status to check progress. **Replace document** creates a new identity; **Remove document** removes it from the draft while its stored bytes remain governed by retention. Neither control is available after submission. An unexpected application-version change preserves your entered answers; reload only after reviewing and confirming any unsaved changes you intend to discard.

Complete the required clean documents, then review and accept the final declarations/consents before submitting. The receipt records immutable document versions, byte counts and digests. Download access is checked again each time and may become unavailable after expiry or another access change.

## Send a public enquiry

Open **Contact and support** in English or Tamil. When the approved enquiry channel is enabled, enter your name, email, optional phone and question, read the linked privacy notice and explicitly check its consent box. No account or document upload is required. A confirmed submission shows an opaque reference. If confirmation fails, the entered details stay available for an explicit retry. If the notice changed, reload and review the current notice before sending. An unavailable form means the channel has not been opened or cannot currently be reached; use only contact information actually published by the team.

## Participant schedule

After staff converts a finalized selected application, sign in and open `/{language}/participant` for the organization. The page shows your application, selection and enrollment journey plus sessions for your enrolled cohorts in chronological order. Online sessions may omit a physical location; in-person and hybrid sessions include staff-provided joining details. You cannot see reviewer scores, comments or internal decision reasons.

## Complete lessons

Start an assigned course to enable its first eligible lessons. Locked lessons show that an earlier prerequisite remains. Mark each available lesson complete; the progress bar and course status update immediately. Completion is safe to retry. The course becomes completed automatically when its published rule is satisfied.

## Take a quiz

Start the assigned course and complete any prerequisite lesson shown for the quiz. Select one answer for every question and submit. The result and best percentage update immediately. A failed attempt can be retried while attempts remain. Passing the quiz or using the final attempt closes further submissions. Quiz status is separate from the current lesson-based course completion rule.

## Submit an assignment

Start the course and complete the assignment lesson's prerequisites. Enter the requested text response. **Assignment files** shows any approved file rule, notice, formats, upload limit and counts. Assignments without a file rule remain text-only, including when file collection is disabled. Assignment results remain separate from the lesson completion percentage.

For configured attachments, select an allowed file and choose **Upload selected file**. Wait for a verified clean result, then explicitly check **Include file** for each file you intend to submit. Uploading alone does not include it. Meet the displayed minimum and maximum before submitting. Pending scans, unsafe files and expired evidence cannot satisfy the requirement or be downloaded. **Refresh saved files** checks progress; automatic scan checks stop after a bounded number of reads.

Keep the original selected file after an interrupted request. **Retry the same metadata request** recovers its original registration. **Review saved file** checks whether bytes were received; choose **Resend the reviewed file** only after reviewing saved state. An active upload lease may prevent an immediate resend. **Resume this saved upload** requires the exact original type, size and digest. Remove an unused staged file before starting a replacement. Your response text remains in the form during file recovery.

A submitted revision cannot be edited. Its file receipt records the immutable version and digest. Wait for trainer feedback before sending another revision; the page shows the score, pass state, feedback and remaining submissions. After an uncertain submission response, read the saved state before submitting again. Later file access still depends on current enrollment, retention and the enabled file service.

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

For other approved file formats, create the ticket first, then use **Secure attachments** in its reply. Collection requires an enabled service and published policy. Read the notice and limits, choose a file and upload it privately. Wait for a clean scan, then explicitly select the file before sending the reply. Uploading alone does not send it. Files retain their original policy edition; each reply selects files from one edition. Pending or unavailable scanning never authorizes attachment or download.

If an upload response is lost, keep the selected file and use **Retry the same upload** to check saved state first. A stale reply retains your text: refresh the ticket, review the latest conversation and send explicitly. Remove an unused staged file; posted evidence cannot be replaced. Files appear only through currently authorized ticket links. Existing TXT attachments continue to work when secure collection is disabled.

Reply when more information is requested. When staff resolve the ticket, close it if the issue is settled. To reopen a resolved or closed ticket, provide a reason; the request returns to the unassigned queue while retaining its history. **Ticket updates** shows in-app notices; mark them read or turn off future notices in this workspace. These are not email/SMS/push messages.

If a save is interrupted, keep your text and use the refresh action before another change. Ticket creation offers recovery of the original request without creating a duplicate. Business profiles and follow-up forms also keep input after errors: use **Refresh saved progress**, compare the saved version and then decide what to save. Each follow-up keeps its own draft. The scheduled dates remain fixed even if staff change the schedule for future profiles; early outcome reporting is allowed and does not move the date. Completed alumni retain access while their participant/enrollment status remains eligible. Public-listing interest does not make a business profile public.

## Record a business baseline and outcome

Open **My business outcomes** from your participant schedule. This form records minimal impact evidence even when you have no business profile. Select your enrollment and a published measurement definition, read the definition, choose Baseline or Outcome and the observation date, then record whether the business has started/is active and how many jobs were created. Enter a reason and save. These observations are self-reported; use the program's approved measurement instructions.

Observation history retains the edition and every revision. **Correct this observation** opens the latest saved version while fixing its original enrollment, date, stage and edition. Your correction adds evidence; it does not erase the earlier report. An edition archived after your original report can still identify a correction. After a stale change, refresh saved evidence and compare with your preserved fields before submitting. After an uncertain response, **Recover request** repeats the exact request without creating another observation. Do not put private financial or identity details in reasons.

Business-profile follow-up reports remain a separate workflow; they are not automatically copied into this evidence or added to its impact totals. Your enrollment/participant status must remain eligible to record evidence. Reporting staff see aggregates and coverage, not your private correction reason.
