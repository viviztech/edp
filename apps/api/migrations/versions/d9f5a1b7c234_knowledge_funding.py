"""K01 knowledge repository and participant funding evidence."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d9f5a1b7c234"
down_revision = "c8e4f0a6b123"
branch_labels = None
depends_on = None


def install_evidence_guards() -> None:
    op.execute("""
        CREATE FUNCTION knowledge_evidence_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'knowledge evidence is append-only'; END $$;
        CREATE TRIGGER knowledge_revision_immutable BEFORE UPDATE OR DELETE ON knowledge_revisions
          FOR EACH ROW EXECUTE FUNCTION knowledge_evidence_immutable();
        CREATE TRIGGER knowledge_interest_immutable BEFORE UPDATE OR DELETE ON knowledge_interests
          FOR EACH ROW EXECUTE FUNCTION knowledge_evidence_immutable();
        CREATE TRIGGER funding_history_immutable BEFORE UPDATE OR DELETE ON funding_history
          FOR EACH ROW EXECUTE FUNCTION knowledge_evidence_immutable();

        CREATE FUNCTION funding_case_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'funding evidence cannot be deleted'; END IF;
          IF TG_OP = 'INSERT' THEN
            IF NEW.status <> 'interested' OR NEW.version <> 1 THEN
              RAISE EXCEPTION 'funding case must begin interested';
            END IF;
            RETURN NEW;
          END IF;
          IF ROW(NEW.id, NEW.organization_id, NEW.participant_id, NEW.item_id, NEW.item_title,
                 NEW.locale, NEW.source, NEW.created_at) IS DISTINCT FROM
             ROW(OLD.id, OLD.organization_id, OLD.participant_id, OLD.item_id, OLD.item_title,
                 OLD.locale, OLD.source, OLD.created_at) THEN
            RAISE EXCEPTION 'funding source and ownership are immutable';
          END IF;
          IF NEW.version <> OLD.version + 1 OR NOT (
             (OLD.status = 'interested' AND NEW.status = 'eligibility_check') OR
             (OLD.status = 'eligibility_check' AND NEW.status = 'document_preparation') OR
             (OLD.status = 'document_preparation' AND NEW.status = 'applied') OR
             (OLD.status = 'applied' AND NEW.status = 'under_review') OR
             (OLD.status = 'under_review' AND NEW.status IN ('approved','rejected')) OR
             (OLD.status = 'approved' AND NEW.status = 'disbursed')) THEN
            RAISE EXCEPTION 'invalid funding status transition';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER funding_case_evidence BEFORE INSERT OR UPDATE OR DELETE ON funding_cases
          FOR EACH ROW EXECUTE FUNCTION funding_case_guard();

        CREATE FUNCTION knowledge_publication_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'knowledge identity cannot be deleted'; END IF;
          IF ROW(NEW.id, NEW.organization_id, NEW.kind, NEW.locale, NEW.slug, NEW.created_at)
             IS DISTINCT FROM
             ROW(OLD.id, OLD.organization_id, OLD.kind, OLD.locale, OLD.slug, OLD.created_at) THEN
            RAISE EXCEPTION 'knowledge identity is immutable';
          END IF;
          IF NEW.version <> OLD.version + 1 THEN
            RAISE EXCEPTION 'invalid knowledge version';
          END IF;
          IF OLD.state <> 'draft' AND (
             (to_jsonb(NEW) - ARRAY['state','version','updated_at','published_at']) IS DISTINCT FROM
             (to_jsonb(OLD) - ARRAY['state','version','updated_at','published_at']) OR
             NEW.state NOT IN ('draft','archived') OR NEW.state = OLD.state) THEN
            RAISE EXCEPTION 'only draft knowledge content can change';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER knowledge_publication_evidence BEFORE UPDATE OR DELETE ON knowledge_items
          FOR EACH ROW EXECUTE FUNCTION knowledge_publication_guard();

        CREATE FUNCTION knowledge_tag_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE parent_state text;
        BEGIN
          IF TG_OP = 'UPDATE' THEN RAISE EXCEPTION 'knowledge tags must be replaced'; END IF;
          SELECT state INTO parent_state FROM knowledge_items
            WHERE id = CASE WHEN TG_OP = 'DELETE' THEN OLD.item_id ELSE NEW.item_id END;
          IF parent_state <> 'draft' THEN
            RAISE EXCEPTION 'published knowledge tags are immutable';
          END IF;
          IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER knowledge_tag_evidence BEFORE INSERT OR UPDATE OR DELETE
          ON knowledge_item_tags
          FOR EACH ROW EXECUTE FUNCTION knowledge_tag_guard();
    """)
    op.execute("""
        INSERT INTO permissions(code) VALUES ('knowledge.manage'), ('funding.manage')
          ON CONFLICT DO NOTHING;
        INSERT INTO role_permissions(role_id, permission_code)
          SELECT id, 'knowledge.manage' FROM roles WHERE name IN
          ('Super Admin','Program Director','Program Manager',
           'Funding Coordinator','Content Manager')
          ON CONFLICT DO NOTHING;
        INSERT INTO role_permissions(role_id, permission_code)
          SELECT id, 'funding.manage' FROM roles WHERE name IN
          ('Super Admin','Program Director','Program Manager','Funding Coordinator')
          ON CONFLICT DO NOTHING;
    """)


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "knowledge_items",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("locale", sa.String(length=2), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("provider", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("eligibility", sa.Text(), nullable=False),
        sa.Column("benefits", sa.Text(), nullable=False),
        sa.Column("sector", sa.String(length=120), nullable=False),
        sa.Column("geography", sa.String(length=120), nullable=False),
        sa.Column("application_process", sa.Text(), nullable=False),
        sa.Column("documents", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("official_url", sa.String(length=2000), nullable=False),
        sa.Column("opens_on", sa.Date(), nullable=True),
        sa.Column("closes_on", sa.Date(), nullable=True),
        sa.Column("last_verified_at", sa.Date(), nullable=False),
        sa.Column("visibility", sa.String(length=16), nullable=False),
        sa.Column("contact", sa.String(length=1000), nullable=False),
        sa.Column("funding_amount_min", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("funding_amount_max", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(funding_amount_min IS NULL OR funding_amount_min >= 0) AND "
            "(funding_amount_max IS NULL OR funding_amount_max >= 0) AND "
            "(funding_amount_min IS NULL OR funding_amount_max IS NULL OR "
            "funding_amount_min <= funding_amount_max) AND "
            "(kind = 'funding' OR (funding_amount_min IS NULL AND funding_amount_max IS NULL))",
            name="knowledge_funding_range",
        ),
        sa.CheckConstraint(
            "(state = 'published') = (published_at IS NOT NULL)", name="knowledge_published_at"
        ),
        sa.CheckConstraint("currency = 'INR'", name="knowledge_currency"),
        sa.CheckConstraint("kind IN ('scheme','funding','opportunity')", name="knowledge_kind"),
        sa.CheckConstraint("locale IN ('en','ta')", name="knowledge_locale"),
        sa.CheckConstraint("state IN ('draft','published','archived')", name="knowledge_state"),
        sa.CheckConstraint("visibility IN ('public','participants')", name="knowledge_visibility"),
        sa.CheckConstraint(
            "opens_on IS NULL OR closes_on IS NULL OR opens_on <= closes_on", name="knowledge_dates"
        ),
        sa.CheckConstraint("version > 0", name="knowledge_version"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id"),
        sa.UniqueConstraint("organization_id", "kind", "slug", "locale"),
    )
    op.create_index(
        "ix_knowledge_catalog",
        "knowledge_items",
        ["organization_id", "locale", "state", "visibility", "id"],
        unique=False,
    )
    op.create_table(
        "funding_cases",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("item_title", sa.String(length=200), nullable=False),
        sa.Column("locale", sa.String(length=2), nullable=False),
        sa.Column("source", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('interested','eligibility_check','document_preparation',"
            "'applied','under_review','approved','rejected','disbursed')",
            name="funding_case_status",
        ),
        sa.CheckConstraint("version > 0", name="funding_case_version"),
        sa.ForeignKeyConstraint(
            ["item_id", "organization_id"],
            ["knowledge_items.id", "knowledge_items.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["participant_id", "organization_id"],
            ["participants.id", "participants.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id"),
        sa.UniqueConstraint("participant_id", "item_id"),
    )
    op.create_index(
        "ix_funding_case_queue", "funding_cases", ["organization_id", "status", "id"], unique=False
    )
    op.create_table(
        "knowledge_interests",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("item_title", sa.String(length=200), nullable=False),
        sa.Column("locale", sa.String(length=2), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["item_id", "organization_id"],
            ["knowledge_items.id", "knowledge_items.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["participant_id", "organization_id"],
            ["participants.id", "participants.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("participant_id", "item_id"),
    )
    op.create_index(
        "ix_knowledge_interest_owner",
        "knowledge_interests",
        ["organization_id", "participant_id", "id"],
        unique=False,
    )
    op.create_table(
        "knowledge_item_tags",
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.ForeignKeyConstraint(
            ["item_id", "organization_id"],
            ["knowledge_items.id", "knowledge_items.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("item_id", "label"),
    )
    op.create_index(
        "ix_knowledge_tag_filter",
        "knowledge_item_tags",
        ["organization_id", "label", "item_id"],
        unique=False,
    )
    op.create_table(
        "knowledge_revisions",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version > 0", name="knowledge_revision_version"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["item_id", "organization_id"],
            ["knowledge_items.id", "knowledge_items.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("item_id", "version"),
    )
    op.create_table(
        "knowledge_saved",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["item_id", "organization_id"],
            ["knowledge_items.id", "knowledge_items.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["participant_id", "organization_id"],
            ["participants.id", "participants.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("participant_id", "item_id"),
    )
    op.create_index(
        "ix_knowledge_saved_owner",
        "knowledge_saved",
        ["organization_id", "participant_id", "id"],
        unique=False,
    )
    op.create_table(
        "funding_history",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version > 0", name="funding_history_version"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["case_id", "organization_id"],
            ["funding_cases.id", "funding_cases.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id", "version"),
    )
    install_evidence_guards()


def downgrade() -> None:
    op.execute("""
        DELETE FROM role_permissions WHERE permission_code IN ('knowledge.manage','funding.manage');
        DELETE FROM permissions WHERE code IN ('knowledge.manage','funding.manage');
        DROP TRIGGER knowledge_tag_evidence ON knowledge_item_tags;
        DROP FUNCTION knowledge_tag_guard();
        DROP TRIGGER knowledge_publication_evidence ON knowledge_items;
        DROP FUNCTION knowledge_publication_guard();
        DROP TRIGGER funding_case_evidence ON funding_cases;
        DROP FUNCTION funding_case_guard();
        DROP TRIGGER funding_history_immutable ON funding_history;
        DROP TRIGGER knowledge_interest_immutable ON knowledge_interests;
        DROP TRIGGER knowledge_revision_immutable ON knowledge_revisions;
        DROP FUNCTION knowledge_evidence_immutable();
    """)
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("funding_history")
    op.drop_index("ix_knowledge_saved_owner", table_name="knowledge_saved")
    op.drop_table("knowledge_saved")
    op.drop_table("knowledge_revisions")
    op.drop_index("ix_knowledge_tag_filter", table_name="knowledge_item_tags")
    op.drop_table("knowledge_item_tags")
    op.drop_index("ix_knowledge_interest_owner", table_name="knowledge_interests")
    op.drop_table("knowledge_interests")
    op.drop_index("ix_funding_case_queue", table_name="funding_cases")
    op.drop_table("funding_cases")
    op.drop_index("ix_knowledge_catalog", table_name="knowledge_items")
    op.drop_table("knowledge_items")
    # ### end Alembic commands ###
