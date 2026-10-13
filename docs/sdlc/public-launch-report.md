# Public launch demo release

Prepared for 14 October 2026 at the user's request. The user confirmed that undecided program policy should use mock data for demonstration. This is a release of the public website and interactive demonstrator; it does not mark the complete EDP platform or deferred milestones as production-accepted.

## What visitors can use

- Redesigned bilingual program discovery, practical resource pages, FAQ and privacy information.
- An explicitly labeled demo of sample profile creation, draft saving, required-field/declaration validation, application submission, a generated demo receipt and a participant workspace.
- Practice lesson completion, sample mentoring-slot selection and application review inside the demo workspace.
- A private six-question idea planner with working English/Tamil text-file downloads.
- Responsive navigation with a primary demo action. Empty news/events and placeholder story/funding sections are removed from the normal visitor journey.

All demo state stays in browser memory. Refreshing clears it. The demo does not ask for a real password or use authentication/application APIs. The program, dates and appointments are explicitly fictional. The production account/session system is separate; real self-service is closed in the UI and BFF until it is configured.

## Deployment and search behavior

`PUBLIC_DEMO_ENABLED=true` is the Coolify Compose default for this public demo deployment. `PUBLIC_SELF_SERVICE_ENABLED=false` closes real signup, verification and reset actions while preserving existing-account sign-in. The web runtime's HTTPS `WEB_ORIGIN` now supplies canonical URLs, language alternates, sitemap and social metadata. Robots and sitemap resolve at request time, avoiding build-time localhost URLs. Demo pages and empty editorial collections are not indexed.

The Next.js configuration retains existing security headers and adds HSTS plus a limited content-security policy blocking external framing, objects, base URLs and form destinations. Public assets remain optimized and self-hosted. No new dependencies, database migrations, database seed data or application secrets were introduced.

## Validation

- Production build and TypeScript passed. ESLint and all 56 frontend tests passed.
- Chrome completed the complete demo journey in English at 1440, 390 and 320 pixels, and in Tamil at 390 pixels. The 320-pixel min-content overflow found during review was corrected.
- Draft validation, receipt creation, lesson completion, mentoring selection and restart passed. No JavaScript errors and no authentication/application API requests occurred in the demo/tool acceptance run.
- Actual English and Tamil planner downloads succeeded with the expected filenames and content. Planner layouts fit 390-pixel screens.
- Screenshots and synthetic downloaded worksheets are kept under `output/playwright/launch-*` and excluded from the commit.

## Real-service prerequisites

The owner has supplied an administrator email and proposed Gmail as sender. No Gmail SMTP credential has been configured, and the existing authentication delivery implementation remains limited to local/test use. A real email adapter, verified provider delivery, an approved active program/application cycle, policies, administrator provisioning and operational backup/restore/monitoring acceptance are required before opening real registration or applications. Public contact details and a custom domain are undecided. No official contact channel has been invented or published.

## Publication

Target: existing `csje-edp` Coolify staging stack on `deploy/coolify`, at https://edp.200.234.34.140.sslip.io/. Record the final commit, deployment and live acceptance below after rollout.
