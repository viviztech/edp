# Six-step completion report

Updated: 2026-10-26 (Asia/Calcutta). Execution follows [the six-step plan](completion-six-step-plan.md). This report distinguishes changes, executed checks and conditions requiring an external environment or named owner.

| Item | Position | Remaining acceptance |
| --- | --- | --- |
| 1. Test stability and final evidence | Local client repair checkpoint passes | Supplemental API refresh was interrupted before completion; prior completed q3 evidence retained; external release gates remain separate |
| 2. Native compilation/device execution | Verified tools, lifecycle repair and native CI prepared | Current Android build result; hosted Android/iOS compile results; real device execution; see [native report](native-completion-report.md) |
| 3. Runtime/providers | Prerequisites inspected | Actual queue/storage/scanner/edge runtime and agreed channel/provider/event implementation and live acceptance |
| 4. Policy/content/owners | Existing configuration and approval boundaries retained | Actual approved rules, content/translations and named operational/UAT owners |
| 5. CI/staging/acceptance | Publication to the owner's requested repository authorized; native compile jobs added | Exact-revision remote results; chosen staging host; scans/load/accessibility/UAT evidence |
| 6. Handover/release | Existing guides/runbooks retained | Completed training/custody, named stabilization owner and target-specific rollback/release approval |

## Current environment findings

- The existing project PostgreSQL 17 cluster was stopped after the prior session. It has been started on loopback only; crash recovery completed before new tests were launched. No production dataset is used.
- Fresh unsuppressed runtime (61 packages), development (101 packages) and npm (795 packages) advisory audits pass with zero findings. Dependency files are unchanged. Evidence: `.local/communications-audit-summary-d714fa30.json`. The initial sandbox network-denied attempt is not a passing audit.
- Docker/Redis are unavailable; WSL reports not installed. No live queue/container runtime can currently be claimed.
- Portable Java, Android command-line tools, API 36/build-tools/platform-tools exist. Gradle and NDK downloads are incomplete. No Android compilation or device pass is inferred from their presence.
- This Windows host has no Xcode/macOS compiler. No connected Android/iOS device or installed emulator has been established.
- Initial restricted-token Git credential lookup could not authenticate. The owner subsequently requested publication to `https://github.com/viviztech/edpdigital`; a normal reviewed Git network check confirms that destination currently has no refs. The existing `origin` remains the separate `edp-digital` repository. Exact-revision CI must be observed after the push and is not counted as passed here.
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

The workflow adds Android debug and unsigned iOS simulator compile jobs, preserving all existing jobs. Local YAML/shell/embedded-Python checks pass. Both jobs retain revision/toolchain identity, logs and hashed artifacts and explicitly exclude device/release acceptance. See [native CI](../testing/native-build-ci.md). The interrupted local Android build had no final APK or compiler result; its cached retry and any later remote result require separate evidence.
