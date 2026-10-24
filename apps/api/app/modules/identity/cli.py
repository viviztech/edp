"""Trusted operator commands. Never expose these through an API."""

import argparse
import getpass
import json
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.identity.models import (
    AuthDelivery,
    Organization,
    Person,
    Role,
    User,
    UserRole,
    VerificationToken,
    now,
)
from app.modules.identity.schemas import Register
from app.modules.identity.security import hasher
from app.modules.identity.service import ROLE_NAMES, audit, delivery_available, seed_roles


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=["seed", "bootstrap-admin", "dev-message", "grant-role", "revoke-role"]
    )
    parser.add_argument("--email")
    parser.add_argument("--name")
    parser.add_argument("--organization")
    parser.add_argument("--organization-id", type=UUID)
    parser.add_argument("--role", choices=ROLE_NAMES)
    args = parser.parse_args()
    settings = get_settings()
    engine = create_engine(settings.database_url.get_secret_value())
    with Session(engine) as db:
        user: User | None
        if args.command == "seed":
            seed_roles(db)
        elif args.command == "bootstrap-admin":
            if not args.email or not args.name or not args.organization:
                parser.error("email, name and organization required")
            data = Register(
                email=args.email,
                display_name=args.name,
                password=getpass.getpass("New administrator password: "),
            )
            if db.scalar(select(User.id).where(User.email == str(data.email))):
                parser.error("Account already exists; use a reviewed role-management operation")
            seed_roles(db)
            person = Person(display_name=data.display_name, locale="en")
            organization = Organization(name=args.organization)
            db.add_all([person, organization])
            db.flush()
            user = User(
                person_id=person.id,
                email=str(data.email),
                status="active",
                password_hash=hasher.hash(data.password.get_secret_value()),
            )
            db.add(user)
            db.flush()
            role = db.scalar(select(Role).where(Role.name == "Super Admin"))
            assert role is not None
            db.add(UserRole(user_id=user.id, role_id=role.id, organization_id=organization.id))
            audit(db, "system.admin_provisioned", "operator-cli", user.id, user.id, organization.id)
            db.commit()
            print("Administrator provisioned. No password or session printed.")
        elif args.command in {"grant-role", "revoke-role"}:
            if not args.email or not args.organization_id or not args.role:
                parser.error("email, organization-id and role required")
            user = db.scalar(select(User).where(User.email == args.email.casefold()))
            org = db.get(Organization, args.organization_id)
            role = db.scalar(select(Role).where(Role.name == args.role))
            if not user or not org or not role:
                parser.error("Account, organization or role not found")
            grant = db.scalar(
                select(UserRole).where(
                    UserRole.user_id == user.id,
                    UserRole.organization_id == org.id,
                    UserRole.role_id == role.id,
                )
            )
            if args.command == "grant-role" and not grant:
                db.add(UserRole(user_id=user.id, organization_id=org.id, role_id=role.id))
                audit(
                    db, "system.role_granted", "operator-cli", resource=user.id, organization=org.id
                )
            elif args.command == "revoke-role" and grant:
                db.delete(grant)
                audit(
                    db, "system.role_revoked", "operator-cli", resource=user.id, organization=org.id
                )
            db.commit()
            print("Role operation completed and audited when changed.")
        else:
            if settings.app_env != "local" or not args.email:
                parser.error("dev-message requires local environment and email")
            row = db.scalar(
                select(AuthDelivery)
                .join(VerificationToken, VerificationToken.id == AuthDelivery.token_id)
                .join(User, User.id == VerificationToken.user_id)
                .where(
                    User.email == args.email.casefold(),
                    VerificationToken.expires_at > now(),
                    VerificationToken.consumed_at.is_(None),
                    AuthDelivery.transport == "development",
                    AuthDelivery.status == "development",
                    AuthDelivery.disposed_at.is_(None),
                )
                .order_by(AuthDelivery.created_at.desc())
                .limit(1)
            )
            if not row:
                parser.error("No pending development message")
            message = json.loads(delivery_available().decrypt(row.encrypted_payload.encode()))
            print(json.dumps(message))  # Explicit trusted local CLI, never application logs.
    engine.dispose()


if __name__ == "__main__":
    main()
