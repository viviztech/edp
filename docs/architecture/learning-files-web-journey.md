# Learning file web journey

The course studio, learner pathway and trainer delivery pages use the typed LMS file endpoints through the existing courses BFF. The browser never receives a provider key, object key, storage version, upload lease or scanner token. Collection stays disabled unless the server explicitly enables it; publishing a file policy does not enable collection.

## Course authoring

An assignment rule begins with an empty policy, minimum and maximum. A staff member with assessment management and file policy view permissions must choose a published `assignment_submission` policy and enter both counts. Existing published rules remain readable without exposing privileged policy lists. Published courses cannot change their rule. A conflict preserves edited counts, requires reading the current saved rule, and requires an explicit decision to use its version before another write.

Private materials use an explicitly chosen `lms_material` policy, lesson, unused position and bilingual labels. The operational upload limit is the smaller of the policy and server bounds. A failed policy lookup can be retried without clearing labels. The author can remove an active draft material with its binding version; the immutable history and reserved position remain visible. Published material rows have no removal control. A lost removal response is reconciled by a metadata read before another command. Pending file operations and unsaved rule edits block publication of their course.

The web authoring screen no longer asks staff to enter legacy provider keys. Existing local/test material references and their authorized delivery path remain compatible. The shared file workflow does not imply a video provider integration.

## Learner submission

The attachment section reads the server's pinned rule, next submission revision, collection setting and `usable` verdict. A file is selected only by an explicit checkbox. Submission serializes all checked `file_ids` alongside the entered response text. Only active usable files for the next revision contribute to the configured minimum and maximum. A course without a file rule continues to support text-only submissions, including when collection is disabled.

Uploads hash the selected bytes before creating metadata. An interrupted metadata response retains the original file, UUID and exact payload; the user can explicitly retry the same metadata request. An interrupted byte response retains the known binding and original bytes. Reading that binding is mandatory before an explicit resend. Both `pending` and `uploading` intents remain recoverable; the backend controls lease expiry and prevents concurrent writes. A recovered quarantined or scanning result is never resent automatically. Security scan checks issue reads only and stop after twenty checks.

A failed list refresh preserves local source bytes while disabling submission. Unknown submission responses require a saved-state refresh before another submit attempt. Successful submission displays the frozen file version and digest returned by the server. Operational file versions can change after submission; the evidence record remains immutable.

## Trainer delivery and scope

Trainer receipts fetch only the current course/submission file collection. Download links require both a usable verdict and frozen evidence. A failed current-access refresh clears links. Request generations prevent a superseded success from restoring links after a later failure or scope change. The byte endpoint repeats the current trainer assignment and permission checks independently of the UI.

Each file widget is keyed by organization, course and its assignment or submission, so navigation cannot reuse an upload recovery payload in another scope. English and Tamil labels and notices share the same controls. Scoped layouts wrap MIME values, UUIDs and digests at mobile widths, and the author/trainer page includes a focusable skip-link target.

## Verification

`apps/web/src/components/learning-files.test.tsx` covers explicit blank rules, usable selections, collection-off compatibility, minimum counts, upload caps and hash matching, metadata and byte response recovery, current file versions, bounded scan polling, removal recovery, policy retry, trainer revocation and stale reads. The isolated `scripts/run-learning-files-browser-test.py` runner reserves ports 8112/3112 and the guarded `edp_learning_files_e2e` database. It injects a controlled scanner only for synthetic fixture bytes; the running API has no fake-clean mode and contacts no scanner provider. The browser script exercises author rules/materials, learner evidence submission, trainer scope, peer denial and English/Tamil layouts at 360, 390, 768 and 1280 pixels.

The Chrome acceptance run passed these paths and exact owner/trainer downloaded-byte assertions. A diagnostic run stalled in Playwright's response-body retrieval after the learner submission had returned 201 and its saved pathway had refreshed. The page does not consume that command's response body. Acceptance therefore retains the 201 and exact outgoing `file_ids` assertions, reads the matching persisted submission through `/my-learning`, and verifies its immutable receipt and downloaded bytes. It does not repeat the submission or change product behavior to accommodate the debugging-protocol wait. Download-event waits and the child process have explicit bounds; diagnostic stack dumps and stage output identify future stalls. With a shared prepared build, the runner verifies standalone asset inventories and SHA-256 digests and skips all artifact copying.
