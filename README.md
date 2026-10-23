# EDP Digital Platform

Center for Social Justice and Equity. FastAPI + Next.js + Flutter, PostgreSQL + Redis/Celery. The authoritative specification is [EDP_CODEX_MASTER_INPUT.md](EDP_CODEX_MASTER_INPUT.md), read in full before implementation.

Backend and web vertical slices cover identity/RBAC/audit, public CMS, CRM/Meta intake, applications/selection, enrollment, learning/assessments/certificates, attendance, mentoring, business plans, knowledge/funding resources, post-training tracking, helpdesk, reporting and impact. Phase 9 closes local web/API acceptance for business profiles, follow-ups, outcomes and support tickets. Phase 10 reporting/impact local web/API acceptance, including the final Tamil responsive review, passed on 2026-10-23. Flutter currently covers authentication and public content; applicant/student/alumni domain workflows and native-device verification remain open. This is a local development implementation, not a production release; external delivery providers and operational release gates remain outstanding.

Latest local completion: [Process 2 web journeys](docs/sdlc/web-journey-completion-report.md), including applicant entry/history, participant navigation, approved-policy-gated enquiries and staff content operations. Shared secure files is next. All commits remain local under the owner's instruction. [Process 1](docs/sdlc/baseline-verification-plan.md) has passing local functional evidence in the [baseline report](docs/sdlc/baseline-verification-report.md); its security/release gates remain open because the dependency gate reports nine high findings from an unpatched transitive `braces` advisory and exact-revision remote CI is deferred under the local-only instruction. The approved continuation order is verified baseline, complete web journeys, shared secure files, communications/jobs, Flutter domain workflows, staging/operations and launch acceptance, followed by approved P1 business tools. Each process requires completion evidence and a progress report before the next begins.

Latest: [Phase 10 reporting and impact](docs/sdlc/milestone-10-report.md), [Phase 9 post-training and helpdesk acceptance](docs/sdlc/milestone-09-report.md), [K01 knowledge and funding acceptance](docs/sdlc/milestone-08-report.md), [B01 acceptance](docs/sdlc/b01-acceptance-report.md), [dependency repair](docs/sdlc/dependency-repair-report.md).

Current work: [Process 3 secure files](docs/sdlc/secure-files-plan.md). The [configurable foundation checkpoint](docs/sdlc/secure-file-foundation-report.md) adds policy administration and private storage/scanner lifecycle; application documents, CMS verified bytes, learning and helpdesk integration remain in progress. Collection and maintenance remain disabled; policy publication does not approve real collection.

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
