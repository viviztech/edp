# ADR 0001 — Modular monolith

Status: accepted for bootstrap under the master specification.

Context: connected EDP workflows, sensitive shared identity and ₹10 lakh development ceiling. The repository has no legacy implementation.

Decision: one FastAPI/Python backend, PostgreSQL, Redis/Celery; one Next.js app and one Flutter app. Organize domain services with explicit boundaries, transactional writes and API contracts. Use Docker Compose locally and simple container deployment initially.

Alternatives: microservices add operational/transaction complexity without capacity evidence. Alternate primary backends conflict with the master. Kubernetes/Kafka are excluded initially.

Consequences: coordinated releases and shared database require module discipline; gain simpler transactions, operations and cost control. Extraction requires measured need, an ADR and migration/ownership plan.
