# Runtime and provider completion checkpoint

Prepared: 2026-10-26 (Asia/Calcutta), for item 3 of the [six-step plan](completion-six-step-plan.md). Basic container/queue smoke acceptance now has remote evidence. Live edge, crash recovery, storage/scanner and external-channel completion remain open. This document records actual boundaries and the next implementable slices; it does not enable a sender or approve real collection.

## Executed and missing runtime acceptance

| Area | Evidence/current implementation | Acceptance still required |
| --- | --- | --- |
| PostgreSQL | Completed historical q3 migration/drift and separate-role restore evidence; the project cluster is available on loopback | Current published-revision backend CI, an accepted staged restore, off-host custody and owner-approved recovery objectives |
| Docker/API/web/queue | The `compose` job on revision `0a113116d6c271ef683a2ebb6de64e79b3d90ab2` passed the actual container build/readiness and `edp.probe` Redis/Celery worker round trip | Exactly-one-Beat observation, queue outage/restart and process-death recovery with fenced effects in the selected staging environment |
| Edge/Linux confinement | Local topology/TLS/proxy contracts and file-confinement tests exist | Actual selected Nginx/TLS/origin/proxy limits, nonroot runtime, mounts/permissions, symlink/path negatives and service isolation |
| Private objects | Version/hash/length/encryption interfaces and controlled adapter tests exist | Actual provider IAM/KMS/versioning, deletion/revocation/hold/backup behavior and compatible object/database recovery |
| Scanning | Bounded ClamD protocol and fail-closed lifecycle implemented/tested with controlled peers | Real signature freshness, unavailable/stale/infected behavior, worker isolation and retained-version negatives |

The exact first publication run is [40273598030](https://github.com/viviztech/edpdigital/actions/runs/40273598030). Its compose, browser, web, operations and secret jobs passed; backend typing and host-dependent mobile goldens failed, and native jobs were consequently skipped. A passing compose job does not establish the other rows above or whole-run acceptance. Later corrected-revision results must be recorded separately.

Local Docker/Redis/WSL remain unavailable. Do not substitute a fake Redis or a direct task-function call for the outstanding runtime rows. The existing runnable entry points are [Compose smoke](../../scripts/compose-smoke.py), [staging contract](../../scripts/deployment_contract.py), [staging evidence](../../scripts/staging_acceptance.py) and [isolated recovery drill](../../scripts/staging_drill.py); deployment operators follow the [staging runbook](../deployment/staging.md).

## Channel implementation boundaries

| Channel/journey | Implemented now | Missing work/input |
| --- | --- | --- |
| Global verification/reset email | Durable encrypted identity intent, bounded verified-TLS SMTP, sending fence, ambiguity reconciliation, safe operator controls and bilingual templates | Approved sender/origin/message/retention configuration and actual recipient acceptance; SMTP acceptance is distinct from receipt |
| CRM/enrollment/helpdesk in-app | Separate recipient-scoped notices, preferences, current authorization and deduplication | These states must continue to mean in-app availability, without being relabeled as email/push delivery |
| Domain email | No separate external enrollment/helpdesk delivery journey exists | A distinct opt-in, approved event/template edition, durable delivery/attempt state, current-recipient recheck and operator reconciliation; existing in-app preference is insufficient |
| FCM | No push-device registry, native Firebase configuration or dispatch implementation exists | Firebase project/app/APNs ownership, session-bound registration/rotation/revocation, permission/lifecycle/tap handling, HTTP v1 OAuth dispatch, bounded retry and actual device observations |
| WhatsApp | No verified owner contact/consent or external send/status journey exists | Approved account/phone/template/contact-verification rules; authenticated, deduplicated callbacks and current-recipient dispatch |
| SMS | No selected vendor contract or live adapter exists | Selected provider/account/sender, exact supported API/error/receipt contract, verified contact/consent and approved event/template/retention rules |

## Next vertical slices after owner inputs

1. Agree the event/channel/recipient and message editions in [OA08/OA09](owner-approval-register.md), plus provider/account configuration references. Keep secret values outside source. These are product/operations inputs, not routine architecture choices that need reapproval.
2. Add one connected domain-email slice using the existing supported SMTP transport. Keep organization notices separate from global authentication delivery. Default external opt-in off, retain exact-version preference/approval edition, and do not backfill old events after opt-in.
3. Persist an immutable notice/channel/message identity, encrypted destination, template edition, expiry, bounded attempts and token/deadline-fenced preparing/sending states. Recheck current user/enrollment/access and both topic/channel preference immediately before I/O. Preserve ambiguous sends for reasoned operator reconciliation; never automatically resend an uncertain accepted effect.
4. Add session-owned push registration and native permission/token/logout handling before FCM dispatch. A provider message name records acceptance, not device receipt. Add explicit deactivation for an unregistered token and distinguish malformed payload errors from token invalidity.
5. Implement approved WhatsApp template send and authenticated status callbacks after the verified-contact flow. Bind callbacks to configured account/phone identity and known deliveries. Provider read status remains separate from the application's notice-read marker.
6. Implement the selected SMS provider against its actual primary contract. Do not invent an HTTP endpoint or claim that an unused interface is a complete integration.
7. Deliver API/database/controlled-peer/worker tests, scoped operator and recipient UI, contracts and bilingual mobile states with each slice. Execute real provider/device/runtime acceptance against approved test recipients before claiming channel completion.

These slices require current authorization, no destinations or message bodies in ordinary logs, task payloads containing IDs only, explicit retention, bounded recovery and owner/organization negatives. A generic adapter without the event/recipient/UI/device journey does not close item 3.

## Primary provider references

- [FCM HTTP v1](https://firebase.google.com/docs/cloud-messaging/send/v1-api), [errors/retries](https://firebase.google.com/docs/cloud-messaging/error-codes), [Flutter configuration](https://firebase.google.com/docs/cloud-messaging/flutter/get-started), [registration lifecycle](https://firebase.google.com/docs/cloud-messaging/manage-tokens).
- [Official Meta Cloud API collection](https://www.postman.com/meta/whatsapp-business-platform/collection/wlk6lh4/whatsapp-cloud-api) and [template-send request](https://www.postman.com/meta/whatsapp-business-platform/request/lwtlz1k/send-message-template-interactive). The selected account/version/template must be checked at implementation time; no free-form messaging entitlement is assumed.
- [Existing notification contract](../integrations/notifications.md) and [identity delivery architecture](../architecture/essential-communications.md).
