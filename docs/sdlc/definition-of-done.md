# Definition of Done

Binding gate for every feature, from master Section 35. A scaffold, endpoint, or mock alone is not a completed feature.

- [ ] Requirement, story and measurable acceptance criteria linked.
- [ ] Schema migration, constraints/indexes, upgrade/downgrade and rollback considerations validated where applicable.
- [ ] Backend and service business rules complete; validated input and explicit error mapping.
- [ ] Permissions and ownership/scope checks implemented and negatively tested.
- [ ] Audit events implemented for consequential actions; no sensitive payload leakage.
- [ ] Scoped web/mobile UI integrated with API, including loading/error/empty states.
- [ ] Localization keys used; English/Tamil parity and accessibility checked.
- [ ] Appropriate unit/integration/workflow/E2E tests executed successfully.
- [ ] OpenAPI/client contract accurate and compatible.
- [ ] Security implications reviewed; no secrets committed; dependency findings triaged.
- [ ] Structured logs, correlation IDs and monitoring/failure visibility added where needed.
- [ ] Documentation and user guidance updated.
- [ ] Lint, typing, tests, migration checks and builds pass; CI green.
- [ ] Manual smoke of the product workflow recorded with environment and result.

Mark each gate passed, failed, blocked or justified N/A with evidence. Missing prerequisites are blockers, not passes. No completed milestone label until all in-scope gates pass. Documentation/design can be delivered while implementation remains incomplete.
