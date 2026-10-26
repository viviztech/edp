# EDP Digital Platform

Center for Social Justice and Equity. FastAPI + Next.js + Flutter, PostgreSQL + Redis/Celery. The authoritative specification is [EDP_CODEX_MASTER_INPUT.md](EDP_CODEX_MASTER_INPUT.md), read in full before implementation.

Backend and web vertical slices cover identity/RBAC/audit, public CMS, CRM/Meta intake, applications/selection, enrollment, learning/assessments/certificates, attendance, mentoring, business plans, knowledge/funding resources, post-training tracking, helpdesk, reporting and impact. Entrepreneur tools now add owner-isolated bilingual cards/catalogues with revocable sharing, immutable decimal quotations/printable artifacts, and private contacts/follow-ups. Flutter source includes applicant, student, support and alumni journeys; its local test/analyzer/JavaScript-build checkpoint passes, while native platform verification remains open. This is a local implementation, not a production release; external services, native devices and operational release gates remain outstanding.

Current execution: [six-step completion](docs/sdlc/completion-six-step-report.md), following the [development closure](docs/sdlc/development-closure-report.md). On 2026-10-26 web passes 490 tests and lint/types/build; mobile passes 189 tests (28 opt-in live skips), clean analysis/formatting and JavaScript build. Recorded full API regression is 404 passed with one POSIX-only skip; its fresh repetition is in progress. Prior strict backend checks, full q3 migration round trip/drift, operations regression, connected bilingual business-tool browser acceptance and separate-role PostgreSQL backup/restore drills pass. Current Python/npm advisory audits report zero findings. Native/device and external release checks remain explicitly open. Earlier [communications](docs/sdlc/essential-communications-report.md), [job recovery](docs/sdlc/background-job-recovery-report.md), [secure files](docs/sdlc/secure-files-acceptance-report.md) and [M02 documents](docs/sdlc/flutter-m02-report.md) retain their historical evidence. Exact-revision remote CI remains unverified. See [ordered progress](docs/sdlc/remaining-development-progress.md).

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
