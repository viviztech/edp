# EDP Digital Platform

Center for Social Justice and Equity. FastAPI + Next.js + Flutter, PostgreSQL + Redis/Celery. The authoritative specification is [EDP_CODEX_MASTER_INPUT.md](EDP_CODEX_MASTER_INPUT.md), read in full before implementation.

Backend and web vertical slices cover identity/RBAC/audit, public CMS, CRM/Meta intake, applications/selection, enrollment, learning/assessments/certificates, attendance, mentoring, business plans, knowledge/funding resources, post-training tracking, helpdesk, reporting and impact. Entrepreneur tools now add owner-isolated bilingual cards/catalogues with revocable sharing, immutable decimal quotations/printable artifacts, and private contacts/follow-ups. Flutter source includes applicant, student, support and alumni journeys; local tests, analysis, JavaScript build and Android debug compilation pass. iOS and native device verification remain open. This is a local implementation, not a production release; external services, native devices and operational release gates remain outstanding.

Current execution: [six-step completion](docs/sdlc/completion-six-step-report.md), following the [development closure](docs/sdlc/development-closure-report.md). On 2026-10-26 local web passes 490 tests and lint/types/build; local mobile passes 189 tests (28 opt-in live skips), clean analysis/formatting and JavaScript build. Recorded full API regression is 404 passed with one POSIX-only skip; a supplemental repetition was interrupted before its final result. The project is published to [viviztech/edpdigital](https://github.com/viviztech/edpdigital). Its first exact-revision CI passes web, secrets, operations, real Compose/queue and connected browser checks; Linux typing and host-dependent goldens exposed portability failures, now corrected locally and awaiting the next remote result. Both strict platform typing targets and 61 focused storage/runtime tests pass. Prior q3 migration/drift and separate-role PostgreSQL backup/restore evidence remains historical; current Python/npm advisory audits report zero findings. Native compile jobs, [owner decisions](docs/sdlc/owner-approval-register.md), [staged UAT](docs/testing/staging-uat.md) and [training/handover](docs/deployment/training-handover.md) are prepared; actual native/device, provider, owner and release gates stay explicit. See [ordered progress](docs/sdlc/remaining-development-progress.md).

Latest: [Phase 10 reporting and impact](docs/sdlc/milestone-10-report.md), [Phase 9 post-training and helpdesk acceptance](docs/sdlc/milestone-09-report.md), [K01 knowledge and funding acceptance](docs/sdlc/milestone-08-report.md), [B01 acceptance](docs/sdlc/b01-acceptance-report.md), [dependency repair](docs/sdlc/dependency-repair-report.md).

Implementation and verification: [Flutter domains](docs/sdlc/flutter-domain-plan.md), [staging operations report](docs/sdlc/staging-operations-report.md), [business tools report](docs/sdlc/business-tools-report.md). Collection and maintenance remain disabled; policy publication does not approve real collection. Real sender activation, Redis/worker/Beat, device, CI, staging, UAT and production-release gates remain explicit.

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
