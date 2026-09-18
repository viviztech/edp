# Privacy data inventory

Owner approvals pending. No real data in development. Default is minimize collection and disable unapproved ingestion; absence of a retention decision is a launch blocker, not permission for indefinite retention.

| Data | Purpose / access | Storage / disposal decision |
|---|---|---|
| Person name, contact, locale | Identity/contact; self and scoped staff | PostgreSQL; approved retention and anonymization schedule pending |
| Password hash, sessions, reset hashes | Authentication; service only | PostgreSQL; expire/revoke; never logs/exports |
| Eligibility, education, business idea | Application review; applicant and assigned reviewers | Relational versioned records; rejected applicant retention pending |
| Identity/supporting documents | Required evidence only; assigned reviewers | Private S3; quarantine, signed access; deletion policy pending |
| Lead attribution/provider metadata | CRM and troubleshooting; assigned staff | Minimal PostgreSQL fields; raw payload retention disabled until configured |
| Scores, private notes, decisions | Accountable selection/mentoring | PostgreSQL; staff visibility separate from participant DTOs |
| Learning/attendance/grades/certificates | Program delivery | PostgreSQL; no precise location/biometrics; retention pending |
| Business outcome/revenue bands | Impact; self and scoped reporting staff | Minimize exact financial data; dated snapshots, aggregate output |
| Consent/preferences/device push tokens | Communication | Versioned consent, revocable preferences; remove stale device tokens |
| Audit and operational logs | Accountability/incident response | Allowlisted metadata; separate access and approved retention |
| Backups | Recovery | Encrypted separate storage; deletion propagates through documented expiry |

Product owner approves field purpose, consent copy, privacy notice, processors, retention periods, data requests and deletion exceptions. Operations owns backups/deletion execution. Engineering owns enforcement and tests. Export/download creates an auditable access event. Public business profile requires explicit opt-in. AI receives no participant data in initial release.
