# Administrator guide ? foundation

An operator provisions an account and exact organization role using the documented CLI; no shared default credentials. Sign in through /en/account or /ta/account. Your organizations lists only current authorized workspaces. Open a workspace to view its name; Audit history is available only with audit.view. Unauthorized or revoked grants are rejected by the backend even if a link is retained.

Account lists current devices and supports per-device, current-device and all-device sign-out. Password reset invalidates every session. In development, verification/reset messages are available through trusted operator CLI, not real email. Publishing/CRM/selection workflows are not yet released. Use synthetic data only until production gates pass.

CMS: open Publishing workspace from the staff page. Choose an organization and page, or create a page with a permanent lowercase address. Select content language, enter title/plain-text body and optional search metadata, then Save draft. Preview shows the saved draft. Publish saved draft updates only that language. Editing does not change published content. Archive requires a reason; restore keeps content as an unpublished draft. Publication history is read-only. A conflict means another edit occurred: select the page again to load current values before reconciling.
