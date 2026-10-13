# EDP Digital Platform

Center for Social Justice and Equity. FastAPI + Next.js + Flutter, PostgreSQL + Redis/Celery. The authoritative specification is [EDP_CODEX_MASTER_INPUT.md](EDP_CODEX_MASTER_INPUT.md), read in full before implementation.

This is the **design baseline and minimum development bootstrap**, not a completed EDP application. Foundation registration/verification/reset, browser/mobile sessions, organization RBAC and audit are implemented for local testing. Email delivery and business workflows remain disabled/unimplemented. Milestone 1 completion still requires the outstanding deployment/device verification gates.

Latest: [foundation authentication report](docs/sdlc/foundation-auth-report.md).

Public launch: the redesigned English/Tamil website now includes an interactive, explicitly labeled demonstration of sample profile creation, applications, learning and mentoring, plus a private idea worksheet. See the [public launch report](docs/sdlc/public-launch-report.md) and [presenter guide](docs/user-guides/public-demo.md). The demonstration does not create real accounts or applications; production email and approved intake policy remain prerequisites for enabling real self-service.

Start with [Milestone 1 report](docs/sdlc/milestone-01-report.md), [local setup](docs/deployment/local.md) and [Milestone 1 plan](docs/sdlc/milestone-01-plan.md).

| Design | Delivery |
|---|---|
| [Product requirements](docs/product-requirements.md) | [Repository audit](docs/sdlc/repository-audit.md) |
| [Architecture and ADRs](docs/architecture/system-architecture.md) | [P0/P1/P2 backlog](docs/sdlc/backlog.md) |
| [PostgreSQL ERD](docs/database/erd.md) | [Definition of Done](docs/sdlc/definition-of-done.md) |
| [Security / RBAC](docs/security/security-model.md) | [Testing strategy](docs/testing/test-strategy.md) |
| [API conventions](docs/api/api-guidelines.md) | [Release gates](docs/sdlc/release-checklist.md) |
| [Privacy inventory](docs/security/privacy-data-inventory.md) | [Open questions](docs/sdlc/open-questions.md) |

Repository: apps/api, apps/web, apps/mobile; packages/api-contracts and design-tokens; infra/docker; docs; scripts; GitHub Actions. Use isolated synthetic data and environment-provided secrets. Never commit .env, provider credentials, uploaded documents or production data. The current web/API stack has an isolated [Coolify staging deployment](docs/deployment/coolify.md); production acceptance gates remain outstanding.
