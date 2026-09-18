# ADR 0004 - Defer native runtime verification without blocking development

Status: accepted by explicit user direction on 2026-09-18.

The user instructed: "ignore the pending tasks. will complete once the development migrated to macos" in the context of unavailable Android/iOS device verification. This overrides the earlier sequencing rule requiring those checks before CMS development. It does not waive the master Definition of Done or production release gates.

Decision: proceed to Milestone 2 with native secure-storage and account lifecycle verification recorded as deferred. Milestone 1 is development-transition accepted with this exception; it is not unconditionally DoD-complete. No other security, testing, privacy or deployment gate is waived. Native checks for subsequent mobile features also require actual evidence before release.

Evidence: native preparation commit 654ac1c passed all six CI jobs in https://github.com/viviztech/edp-digital/actions/runs/35372311536 and was fast-forwarded into main. The integration test compiles as an Android APK, but has not run on a device. See [native acceptance](../../testing/native-session-acceptance.md).

Re-entry gate: after macOS migration, engineering runs Android and iOS native storage tests and the documented account lifecycle matrix, records OS/device/commit/results, fixes failures and obtains the designated release review. Use synthetic data. No invented deadline or claim that macOS migration alone constitutes verification. Retain the tests and checklist in source control.
