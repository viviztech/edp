"""Local synthetic application form provisioning. Never use for production policy."""

import argparse
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.applications.models import (
    ApplicationAcknowledgementDefinition,
    ApplicationField,
    ApplicationForm,
)
from app.modules.identity.models import Organization, now


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["seed-demo"])
    parser.add_argument("--organization-id", type=UUID, required=True)
    args = parser.parse_args()
    settings = get_settings()
    if settings.app_env != "local":
        parser.error("Synthetic application forms are local-development only")
    with Session(create_engine(settings.database_url.get_secret_value())) as db:
        organization = db.get(Organization, args.organization_id)
        if not organization:
            parser.error("Organization not found")
        existing = db.scalar(
            select(ApplicationForm).where(
                ApplicationForm.organization_id == organization.id,
                ApplicationForm.state == "published",
            )
        )
        if existing:
            print("A published form already exists; no change made.")
            return
        form = ApplicationForm(
            organization_id=organization.id,
            version=1,
            state="draft",
            title_en="Entrepreneurship application draft",
            title_ta="தொழில்முனைவு விண்ணப்பம்",
            published_at=now(),
        )
        db.add(form)
        db.flush()
        db.add_all(
            [
                ApplicationField(
                    form_id=form.id,
                    field_key="business_idea",
                    section_key="proposal",
                    label_en="Describe your business idea",
                    label_ta="உங்கள் வணிக யோசனையை விவரிக்கவும்",
                    field_type="textarea",
                    required=True,
                    position=1,
                ),
                ApplicationField(
                    form_id=form.id,
                    field_key="experience",
                    section_key="background",
                    label_en="Relevant experience",
                    label_ta="தொடர்புடைய அனுபவம்",
                    field_type="textarea",
                    required=False,
                    position=2,
                ),
                ApplicationField(
                    form_id=form.id,
                    field_key="funding_requirement",
                    section_key="proposal",
                    label_en="Estimated funding requirement",
                    label_ta="மதிப்பிடப்பட்ட நிதித் தேவை",
                    field_type="number",
                    required=False,
                    position=3,
                ),
            ]
        )
        db.add_all(
            [
                ApplicationAcknowledgementDefinition(
                    form_id=form.id,
                    acknowledgement_key="final_declaration",
                    kind="declaration",
                    label_en="I declare that the information in this application is accurate.",
                    label_ta="இந்த விண்ணப்பத் தகவல் சரியானது என்று அறிவிக்கிறேன்.",
                    required=True,
                    position=1,
                ),
                ApplicationAcknowledgementDefinition(
                    form_id=form.id,
                    acknowledgement_key="application_consent",
                    kind="consent",
                    label_en="I consent to processing this information for my application.",
                    label_ta="என் விண்ணப்பத்திற்காக இந்தத் தகவலை செயலாக்க ஒப்புக்கொள்கிறேன்.",
                    required=True,
                    position=2,
                ),
            ]
        )
        db.flush()
        form.state = "published"
        form.published_at = now()
        db.commit()
        print("Synthetic local application policy created with declaration and consent.")


if __name__ == "__main__":
    main()
