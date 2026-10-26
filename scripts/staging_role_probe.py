"""Child-only synthetic probes using the supplied API or worker runtime identity."""

import os
import secrets
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/api"))


def main() -> None:
    from app.core.config import get_settings
    from app.modules.identity.models import AuditLog, Organization
    from app.modules.programs.models import DomainOutbox
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    engine = create_engine(get_settings().database_url.get_secret_value())
    if os.environ["EDP_DRILL_RUNTIME"] == "api":
        from app.main import app
        from fastapi.testclient import TestClient

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"ops-{uuid4().hex}@example.com",
                    "password": secrets.token_urlsafe(24),
                    "display_name": "Synthetic role drill",
                    "locale": "en",
                },
            )
            assert response.status_code == 202, "runtime registration failed"
        with Session(engine) as db:
            org = Organization(name="Synthetic operations drill")
            db.add(org)
            db.flush()
            db.add(
                AuditLog(
                    organization_id=org.id,
                    action="ops.drill",
                    resource_id=uuid4(),
                    request_id="synthetic-ops-drill",
                )
            )
            db.add(
                DomainOutbox(
                    organization_id=org.id,
                    event_key=f"ops.drill:{uuid4()}",
                    event_type="ops.fixture",
                    aggregate_type="ops",
                    aggregate_id=uuid4(),
                    payload="{}",
                )
            )
            db.commit()
    else:
        from app.modules.crm.export_service import recover_exports
        from app.modules.identity.delivery_service import recover
        from app.modules.notifications.participant_service import consume_pending
        from sqlalchemy import text

        with engine.begin() as db:
            for table in (
                "users",
                "verification_tokens",
                "user_roles",
                "role_permissions",
                "participants",
                "enrollments",
                "applications",
                "notification_preferences",
                "participant_notice_preferences",
            ):
                db.execute(text(f"SELECT 1 FROM {table} FOR UPDATE"))

        with Session(engine) as db:
            consume_pending(db)
        with Session(engine) as db:
            recover_exports(db, get_settings())
        with Session(engine) as db:
            recover(db, get_settings())
    engine.dispose()


if __name__ == "__main__":
    main()
