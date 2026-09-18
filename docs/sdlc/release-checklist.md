# Release checklist

## Every pull request
- [ ] Requirement/story and acceptance linked; DoD evidence.
- [ ] Tests, migration impact, security impact, API changes, UI evidence, documentation and rollback considered.
- [ ] No secrets, real user data or build output committed.

## Staging gate (master Section 41)
- [ ] CI green across backend/web/mobile and scans.
- [ ] Migrations upgraded/downgraded in disposable DB; production-safe rollback plan.
- [ ] Synthetic role/program/cohort/course/content/journey data validated.
- [ ] Critical E2E and negative authorization journeys pass.
- [ ] No known high-severity security issue; environment validated.

## Production additional gate
- [ ] Client-approved UAT and privacy/consent copy.
- [ ] Backups enabled and restore rehearsed with measured RPO/RTO.
- [ ] Monitoring/error tracking, TLS/DNS and incident runbook.
- [ ] Meta production webhook and push configuration validated.
- [ ] Admins securely provisioned; privileges reviewed.
- [ ] Rollback plan, previous artifacts and compatible data migrations.
- [ ] User/admin training, guides, handover and stabilization owner.

Unchecked gates block release. Bootstrap is not a production deployment.
