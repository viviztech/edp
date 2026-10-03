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
