# Six-step completion report

Updated: 2026-10-26 (Asia/Calcutta). Execution follows [the six-step plan](completion-six-step-plan.md). This report distinguishes changes, executed checks and conditions requiring an external environment or named owner.

| Item | Position | Remaining acceptance |
| --- | --- | --- |
| 1. Test stability and final evidence | Local repairs pass; first remote run exposed portability failures, corrected locally | Corrected-revision remote results; supplemental local full API refresh was interrupted before completion |
| 2. Native compilation/device execution | Android debug build passes with unchanged source; iOS lifecycle repair and native CI prepared | Hosted compile results, iOS compilation and real device execution; see [native report](native-completion-report.md) |
| 3. Runtime/providers | Real remote Compose/queue smoke passes; [remaining runtime/provider work](runtime-provider-completion.md) is explicit | Service crash/recovery/TLS/storage/scanner acceptance; selected external providers/contact/consent and connected channel implementation |
| 4. Policy/content/owners | [Owner decision packet](owner-approval-register.md) prepared with actual field/config mappings | All 12 attributable owner decisions remain pending; real content/privacy/retention rules and named owners required |
| 5. CI/staging/acceptance | Project pushed to requested repository; first exact-revision CI reviewed and confirmed failures repaired | Corrected-revision CI and native compile; selected staging environment and execution of [UAT packet](../testing/staging-uat.md), performance/accessibility/restore acceptance |
| 6. Handover/release | [Training/handover packet](../deployment/training-handover.md) prepared, including custody and rollback exercises | Actual training/demonstration, custody acknowledgements, stabilization owner and target-specific release approval |

## Current environment findings

- The existing project PostgreSQL 17 cluster was stopped after the prior session. It has been started on loopback only; crash recovery completed before new tests were launched. No production dataset is used.
- Fresh unsuppressed runtime (61 packages), development (101 packages) and npm (795 packages) advisory audits pass with zero findings. Dependency files are unchanged. Evidence: `.local/communications-audit-summary-d714fa30.json`. The initial sandbox network-denied attempt is not a passing audit.
- Docker/Redis are unavailable; WSL reports not installed. No live queue/container runtime can currently be claimed.
- Portable Java, Android command-line tools, API 36/build-tools/platform-tools and complete verified Gradle/NDK archives are available. The cached Android debug compilation passes with unchanged Android/Dart source. Additional API 34/35 dependency SDKs are installed inside the workspace by Gradle.
- This Windows host has no Xcode/macOS compiler. No connected Android/iOS device or installed emulator has been established.
- The owner requested publication to `https://github.com/viviztech/edpdigital`. The destination was initially empty. Selecting the existing `viviztech` account resolved Git Credential Manager's ambiguity between two cached accounts. Revision `0a113116d6c271ef683a2ebb6de64e79b3d90ab2` was pushed to `main` and verified by `ls-remote`; no force push occurred. The existing `origin` remains the separate `edp-digital` repository.
- No selected staging host/domain or configured provider credentials were discovered. Secret values are not included in this report.

The owner has been asked for device/Mac access, existing environment/provider configuration locations and approved rules/UAT ownership while independent local work continues. A lack of an answer does not constitute approval or a successful external check.

## Item 1 - client repair checkpoint

- Web: the document-readiness test now waits for the readiness effect after rendering clean state, preserving exact upload/write assertions. The application-definition recovery fixture now includes real contract-shaped IDs/positions, eliminating its React key warning. No production web logic was changed. Focused 12 cases and full 490 cases in 81 files pass; ESLint, TypeScript and the production build pass. Evidence: `.tool-cache/completion-step1-web/acceptance.json`; built artifact `9HK7swURorCWnfeCROL_R`.
- Mobile: an injectable current-time function preserves production UTC date behavior while pinning date-sensitive fixtures. The existing Tamil golden was not changed. The storage retry interaction settles the viewport and verifies the button is hittable before tapping; input-preservation assertions remain. Five missing-brace findings were fixed. All 189 tests pass, with 28 opt-in live tests skipped; formatting checks 97 files, analysis has no findings, localization outputs regenerate unchanged and the JavaScript web build passes. Evidence: `.tool-cache/completion-step1-mobile/`.
- Contract export was repeated twice. OpenAPI SHA-256 is `6ea0802b512a5cc1b47f66e19cc718896a70c8e944c0f021d20570e143e9d2d3`; TypeScript SHA-256 is `0a7fa7aeda5cbfae3bf4c3f730f825d52fe80a1ddee714d2716b74edadf4f7d5`. Both exports are deterministic and byte-identical to the existing files.
- No API/schema/dependency change was needed for these repairs. A supplemental full API regression reached 91% without a recorded failure before session interruption; it has no final result and is not counted as passed. A supplemental current-artifact business-tool browser attempt was also interrupted without a final report. Prior completed final q3 evidence remains 404 passed and one POSIX-only skip; prior connected browser acceptance remains historical evidence.
- Scoped source scan: 968 selected source files, zero findings, no ignored rules or suppressions; `.local/completion-step1-source-scan.json`. The initial scan identified three historical schema digests as generic keys because of their labels. Only the labels were clarified to `Exported schema SHA-256`; all historical hashes were preserved, then the complete selected source was scanned again successfully. Later checkpoint changes require their own final scan.

The mobile/web repair checkpoint is verified and reported before item 2. Native build/device acceptance, the optional Wasm secure-storage limitation and live service/CI/UAT conditions are not closed by a JavaScript compilation.

## Item 2 - native source and CI preparation

Official Gradle and NDK archives are now complete and checksum-verified, with workspace-only tool extraction. The iOS private-file bridge now receives engine detach callbacks, immediately cancels pending provider/picker work and cleans scoped files on its serial queue. The source-level review does not establish iOS compilation or device behavior. A reviewed ADB invocation successfully reports zero attached devices; its newly owned daemon was stopped.

The workflow adds Android debug and unsigned iOS simulator compile jobs, preserving all existing jobs. Local YAML/shell/embedded-Python checks pass. Both jobs retain revision/toolchain identity, logs and hashed artifacts and explicitly exclude device/release acceptance. See [native CI](../testing/native-build-ci.md). The cached local Android retry passes: APK 165,530,645 bytes, SHA-256 `ce4b427780cf07f4aa354d52457f744bf57dc81fed4c7958b5a971974695d526`, with identical before/after Android source manifests. Its initial interrupted attempt remains excluded. Exact proof is `.tool-cache/completion-step2-native/acceptance.json`; iOS and device checks remain separate.

## First publication and portability repairs

[Run 40273598030](https://github.com/viviztech/edpdigital/actions/runs/40273598030) tests the exact first published revision. Web, secrets, operations, Compose/real Redis-Celery probe, authentication/browser and private-file browser jobs pass. The run as a whole fails: backend MyPy checks Windows-specific attributes under Linux, and the mobile job compares Windows-captured font goldens on Ubuntu. Native jobs are skipped because their prerequisite mobile job fails. These are actual results, not waived gates.

- Backend storage dispatch now uses statically understood platform guards, and Windows helpers reject unsupported platforms before native imports. Windows handle protections and POSIX no-follow/locking/version checks remain intact. Strict MyPy targets Linux and Windows successfully across all 147 app files; Ruff/format pass and focused storage/runtime acceptance passes 61 tests with one existing Windows/POSIX skip. Evidence: `.tool-cache/completion-ci-backend/acceptance.json`. No schema or contract change was needed.
- The canonical mobile visual job now uses pinned Windows 2022 with the same Flutter SDK as the unchanged strict baselines. It retains all 189 ordinary tests, format/analysis/lock/build checks and failure diagnostics. Other jobs, including native Ubuntu/macOS compilation, remain unchanged. YAML and eight PowerShell blocks parse successfully; no golden masters, Dart/native code or dependencies changed. The actual corrected Windows run remains required. See [golden environment](../testing/mobile-goldens.md).
- Owner, UAT and training/handover packets are reviewable preparations. Their pending approvals and unexecuted exercises are not counted as acceptance. External-channel implementation dependencies and the initial synthetic-only staging contract remain explicit.
