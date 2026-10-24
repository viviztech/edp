# EDP Digital Platform

Center for Social Justice and Equity. FastAPI + Next.js + Flutter, PostgreSQL + Redis/Celery. The authoritative specification is [EDP_CODEX_MASTER_INPUT.md](EDP_CODEX_MASTER_INPUT.md), read in full before implementation.

Backend and web vertical slices cover identity/RBAC/audit, public CMS, CRM/Meta intake, applications/selection, enrollment, learning/assessments/certificates, attendance, mentoring, business plans, knowledge/funding resources, post-training tracking, helpdesk, reporting and impact. Phase 9 closes local web/API acceptance for business profiles, follow-ups, outcomes and support tickets. Phase 10 reporting/impact local web/API acceptance, including the final Tamil responsive review, passed on 2026-10-23. Flutter currently covers authentication and public content; applicant/student/alumni domain workflows and native-device verification remain open. This is a local development implementation, not a production release; external delivery providers and operational release gates remain outstanding.

Latest local completion: [essential communications](docs/sdlc/essential-communications-report.md), step 3 of the authorized six-process sequence, accepted on 2026-10-24 after [background-job recovery](docs/sdlc/background-job-recovery-report.md) and [secure files](docs/sdlc/secure-files-acceptance-report.md). Configured global identity SMTP and the enrollment participant inbox pass 368 API tests (one POSIX skip), 464 web tests, controlled protocol checks and connected browser acceptance. Fresh npm and complete Python runtime/development audits report zero findings. All commits remain local; exact-revision remote CI remains deferred. See [ordered progress](docs/sdlc/remaining-development-progress.md).

Latest: [Phase 10 reporting and impact](docs/sdlc/milestone-10-report.md), [Phase 9 post-training and helpdesk acceptance](docs/sdlc/milestone-09-report.md), [K01 knowledge and funding acceptance](docs/sdlc/milestone-08-report.md), [B01 acceptance](docs/sdlc/b01-acceptance-report.md), [dependency repair](docs/sdlc/dependency-repair-report.md).

Current work: [Flutter domain journeys](docs/sdlc/flutter-domain-plan.md), then [staging operations and launch acceptance preparation](docs/sdlc/staging-operations-plan.md), followed by locally authorized P1 business tools. Collection and maintenance remain disabled; policy publication does not approve real collection. Real sender activation, Redis/worker/Beat, device, CI, staging, UAT and production-release gates remain explicit.

Start with [Milestone 1 report](docs/sdlc/milestone-01-report.md), [local setup](docs/deployment/local.md) and [Milestone 1 plan](docs/sdlc/milestone-01-plan.md).

| Design | Delivery |
|---|---|
| [Product requirements](docs/product-requirements.md) | [Repository audit](docs/sdlc/repository-audit.md) |
| [Architecture and ADRs](docs/architecture/system-architecture.md) | [P0/P1/P2 backlog](docs/sdlc/backlog.md) |
| [PostgreSQL ERD](docs/database/erd.md) | [Definition of Done](docs/sdlc/definition-of-done.md) |
| [Security / RBAC](docs/security/security-model.md) | [Testing strategy](docs/testing/test-strategy.md) |
| [API conventions](docs/api/api-guidelines.md) | [Release gates](docs/sdlc/release-checklist.md) |
| [Privacy inventory](docs/security/privacy-data-inventory.md) | [Open questions](docs/sdlc/open-questions.md) |

Repository: apps/api, apps/web, apps/mobile; packages/api-contracts and design-tokens; infra/docker; docs; scripts; GitHub Actions. Use isolated synthetic data and environment-provided secrets. Never commit .env, provider credentials, uploaded documents or production data. No deploy or live provider operation has been performed.
