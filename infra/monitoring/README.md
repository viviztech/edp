# Operations signals and local alert acceptance

[`signals.json`](signals.json) defines a bounded signal catalog with no recipient,
live endpoint or invented SLO. Thresholds and responder/escalation ownership require
actual measurements and owner approval. External delivery stays disabled. Database
readiness, Redis ping, actual worker round trip, scheduler count, outbox age, scanner
freshness, backup and restore age are separate signals. Missing samples are
unavailable, never passing zeroes.

`scripts/collect_operations.py` collects fixed read-only aggregates from an explicit
synthetic loopback database using `EDP_OPERATIONS_DATABASE_URL`. It refuses live/
shared development targets and bounds connection, statement and lock timeouts.
`--redis` optionally pings loopback `EDP_OPERATIONS_REDIS_URL`; it does not prove a
worker round trip. Worker/Beat/scanner/backup checks remain null unless actually
executed. No provider is contacted. Use fresh output paths:

```text
python scripts/collect_operations.py --output .local/operations-snapshot.json
python scripts/operations_monitor.py .local/operations-snapshot.json --output .local/operations-alerts.json
```

The evaluator rejects stale (>300 seconds), future, malformed/nonfinite, unknown
and nonsynthetic samples. It records fixed signal/runbook codes locally. Missing
approved thresholds remain unconfigured. Regression fixtures inject database/Redis
failure, two schedulers, delayed outbox and recovery; no external alert is sent.

For actual infrastructure export these bounded aggregates through an approved
collector to the selected Prometheus/Grafana/error-tracking system. Dashboards must
cover API/web/edge error/saturation, PostgreSQL, worker/one-Beat/queue, files/scanner,
safe communication failure/ambiguity and backup verification. Keep domains, paths,
queries, user/org identifiers, destinations, document names, object keys,
capabilities and provider payloads out of labels, alerts and error tracking.

Each alert needs a responder, escalation, measured threshold/window and
[incident runbook](../../docs/deployment/incident-response.md). Test routing in a
recording sink before explicitly approved delivery. No live dashboard, error
tracking or external alert integration has been activated.
