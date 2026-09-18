# Milestone 1 — Design baseline and platform foundation

Scope for this execution: Section 38 Steps 1–5 and available Step 7 verification. User explicitly requests documentation/architecture first, then minimum development bootstrap. Step 6 full authentication/RBAC/audit vertical slice is a separate completion gate within Milestone 1; do not expose dummy auth or mark it done.

## Ordered work and acceptance

1. Audit empty repository and preserve master input. Evidence: repository-audit.md.
2. Produce PRD, prioritized stories, DoD/release gates, ERD, architecture/ADRs, API/security/privacy/testing and operations plans. All use stable person identity, scoped RBAC and outbox transactions consistently.
3. Present architecture, boundaries, risks and this plan before coding. Review consistency; record open policies without fabricating answers.
4. Bootstrap FastAPI/Pydantic/SQLAlchemy/Alembic, PostgreSQL/Redis/Celery Compose, Next.js strict TS, Flutter shell, English/Tamil, safe env, quality config, initial tests, CI and OpenAPI export. No domain schema generated wholesale.
5. Verify available lint/type/test/build and migration checks. Missing Docker/toolchain/service access remains explicit blocker. Report evidence and stop before the next major milestone.

## Remaining foundation slice (F02/F03)

Before claiming Milestone 1 complete: Person/User and scoped role/session/audit migrations; registration/verification/login/reset/logout; refresh replay/revocation; throttles; transactional audit; protected admin shell; web BFF and Flutter secure sessions; synthetic role seed; complete API/client integration and negative authorization tests. Migration upgrade/downgrade, full CI, manual smoke and Compose tests must pass. No real messaging credentials necessary: adapters and sandbox fixtures.

Bootstrap acceptance is not feature DoD or production readiness. No CRM/CMS/LMS or selection implementation in this pass. RPO/RTO, retention, branding, providers and policies remain tracked. Next major milestone is CMS/public only after full foundation gate passes.

## Continuation status

F02/F03 local authentication, RBAC, audit and client integration are now implemented. See [continuation report](foundation-auth-report.md) and [acceptance plan](foundation-auth-plan.md). Milestone closure remains blocked by unexecuted CI/Compose/device gates, not by a claim that business features are complete.
