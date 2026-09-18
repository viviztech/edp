# Production deployment plan

Not deployable as production until DoD and release gates pass. Deploy tested immutable artifacts, least-privilege DB runtime separate from migration credentials, private Redis, private object storage and TLS reverse proxy. Production disables public OpenAPI/internal diagnostics. Environment separates secrets/data from staging. Configure security headers, request limits, backups/error tracking/monitoring and alerts with named responders. Scale API/workers independently after measurements; one scheduler.

Release: client UAT → backup verification → compatible migration → rollout → health and critical smoke → monitor. Rollback prefers previous application image with backward-compatible schema; destructive schema downgrade requires reviewed recovery plan and tested backup. Never run local Compose as an assumed hardened public deployment. Document recurring hosting/storage/provider costs before provisioning.
