# Flutter domain client implementation

Authority: [Flutter journey plan](../sdlc/flutter-domain-plan.md), current API contracts and server authorization. Prerequisite local checkpoints are secure files `74fb149`, jobs `679ebdc`, and communications `832ca3f`. M00 establishes client/session/navigation, followed by applicant/files, learning/attendance, participant support and alumni journeys. Native platform and release gates remain separate.

## Shared client contract

The session owner retains the access token in memory and refresh token only in the OS secure store, serializes refresh rotation and invalidates private feature state with a session epoch. Restoring, signed out, authenticated and temporarily unavailable states remain distinct. Profiles consume actual server locale and organization permission grants; role names never grant access.

Authenticated feature repositories use one relative-path API transport. Safe reads can recover authentication; commands send at most once and distinguish not sent, rejected and uncertain outcomes. Features reconcile their exact server object before an explicit retry. Public content uses a separate unauthenticated transport. Redirects, foreign returned URLs, traversal and token-bearing logs are rejected. Feature models own their typed endpoints and validation; there is no generic workflow engine.

The native file layer snapshots selected streams into bounded app-private temporary bytes, hashes those exact bytes, preserves immutable intent identity and uses the typed domain raw MIME/If-Match endpoints. Polling is bounded and paused in background. Process death discards transient selection; a filename never proves recovery. Download/open always reauthorizes and never forwards bearer credentials to an external viewer.

## Localization and acceptance

English/Tamil ARB source files are authoritative; generate Dart localization files with the cached supported Flutter toolchain. Local validation includes format, analysis, unit/widget tests, actual guarded API repository journeys and responsive/large-text screenshots. JavaScript web compilation is a compile check; native secure-storage, file provider/camera, system deep links, Android/iOS execution and release signing need their own evidence. No push-device contract exists in the accepted API, so in-app updates never imply FCM delivery.
