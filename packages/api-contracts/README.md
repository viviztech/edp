# API contracts

Generate from actual FastAPI routes: `python scripts/export-openapi.py` with configured API environment. Bootstrap contains only probe contracts. Generate web TypeScript using `npm run contracts` in apps/web. Commit generated schema/types and inspect diffs. Evaluate Dart generation with the authentication slice; never fabricate user/session contracts in clients. Health routes are not the future domain API.
