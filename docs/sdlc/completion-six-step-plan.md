# Six-step completion execution

Recorded: 2026-10-26 (Asia/Calcutta). The owner requested completion of the six outstanding work items in the project-status review, one by one. This sequence follows that request and preserves existing source, synthetic data and the FastAPI/PostgreSQL/Next.js/Flutter architecture.

| Order | Work | Acceptance |
| --- | --- | --- |
| 1 | Fix current mobile failures and web test instability; reconcile final evidence | Deterministic date-sensitive mobile tests, reachable retry interaction, clean formatting/analyzer, full mobile and web suites, relevant lint/types/builds, current contracts and source/dependency evidence. No weakened assertions or blindly replaced goldens. |
| 2 | Native compilation and device verification | Attempt supported Android compilation with verified workspace-local tools; record artifact identity and real device availability. iOS requires macOS/Xcode. Execute available secure-storage/session/file/camera/deep-link checks; retain each unavailable platform gate explicitly. |
| 3 | External runtime and provider completion | Validate available isolated queue/storage/scanner/edge runtimes. Complete provider-neutral missing integration work against official contracts and controlled peers. Live accounts, approved recipients and provider configuration are required for actual external acceptance. |
| 4 | Product, privacy and operational decisions | Prepare concrete configurable policy/content/translation and owner-decision material from existing implementation. Record actual owner approvals; never infer legal approval or invent business rules. |
| 5 | CI, staging, security, performance, accessibility and UAT | Prepare final revision and runnable evidence; execute available checks. Remote publication, hosting, staging environment and named UAT owners must be resolved before claiming corresponding gates. |
| 6 | Training, handover, rollback and release | Deliver reviewable guides, training/handover and rollback evidence. Actual attendance, custody, ownership and deployment approval require their named owners and selected target. |

Start each implementation item only after its preceding locally executable checkpoint is verified and reported. Independent read-only investigation of later prerequisites can proceed concurrently. An unavailable external condition does not count as passed and does not prevent independent authorized preparation for subsequent items.

On 2026-10-26 the owner explicitly authorized pushing the project to `https://github.com/viviztech/edpdigital`. Preserve the separate existing `edp-digital` origin and publish a coherent reviewed project revision to the requested repository. This resolves the earlier local-only source-publication boundary for that destination. Do not send real messages, collect personal data, purchase/provision services, submit to stores or deploy to an unspecified environment. The master specification and release checklist remain binding.

## Baseline and known failures

The 2026-10-26 audit found five Flutter analyzer missing-brace findings; a Tamil impact golden depending on the wall clock; a storage-protection retry test tapping outside the viewport; and an intermittent web document-readiness assertion. The full web suite passed 490 cases with two workers after an initial 489/490 run. Prior full API/q3 evidence is 404 passed and one POSIX-only skip. These are baseline observations, not completion evidence for new changes.

Execution results and exact remaining dependencies are recorded in `completion-six-step-report.md` as each checkpoint is verified.
