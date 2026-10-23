"""Versioned enquiry inbox and scoped management permission."""

import sqlalchemy as sa
from alembic import op

revision = "g2c8d4e0f567"
down_revision = "f1b7c3d9e456"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contact_enquiries", sa.Column("version", sa.Integer(), server_default="1", nullable=False)
    )
    op.add_column(
        "contact_enquiries", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.execute("UPDATE contact_enquiries SET updated_at = created_at")
    op.alter_column("contact_enquiries", "updated_at", nullable=False)
    op.alter_column("contact_enquiries", "version", server_default=None)
    op.create_check_constraint("enquiry_version", "contact_enquiries", "version > 0")
    op.create_index(
        "ix_contact_enquiries_queue", "contact_enquiries", ["organization_id", "status", "id"]
    )
    op.execute("""
        CREATE FUNCTION enquiry_lifecycle_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'INSERT' THEN
            IF NEW.status <> 'new' OR NEW.version <> 1 THEN
              RAISE EXCEPTION 'received enquiry must start new at version one'; END IF;
            RETURN NEW;
          END IF;
          IF (to_jsonb(NEW) - ARRAY['status','version','updated_at']) IS DISTINCT FROM
             (to_jsonb(OLD) - ARRAY['status','version','updated_at']) THEN
            RAISE EXCEPTION 'received enquiry content is immutable'; END IF;
          IF NEW.version <> OLD.version + 1 OR NOT (
              (OLD.status = 'new' AND NEW.status = 'reviewed') OR
              (OLD.status = 'reviewed' AND NEW.status = 'closed')) THEN
            RAISE EXCEPTION 'invalid enquiry lifecycle'; END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER enquiry_lifecycle BEFORE INSERT OR UPDATE ON contact_enquiries
          FOR EACH ROW EXECUTE FUNCTION enquiry_lifecycle_guard();
        INSERT INTO permissions(code) VALUES ('enquiry.view'), ('enquiry.manage')
          ON CONFLICT DO NOTHING;
        INSERT INTO role_permissions(role_id, permission_code)
          SELECT id, permission FROM roles CROSS JOIN
            (VALUES ('enquiry.view'), ('enquiry.manage')) AS grants(permission)
          WHERE name IN ('Super Admin','Program Director','Program Manager','Support Executive')
          ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("""
        DROP TRIGGER enquiry_lifecycle ON contact_enquiries;
        DROP FUNCTION enquiry_lifecycle_guard();
        DELETE FROM role_permissions WHERE permission_code = 'enquiry.manage';
        DELETE FROM permissions WHERE code = 'enquiry.manage';
    """)
    op.drop_index("ix_contact_enquiries_queue", table_name="contact_enquiries")
    op.drop_constraint("enquiry_version", "contact_enquiries", type_="check")
    op.drop_column("contact_enquiries", "updated_at")
    op.drop_column("contact_enquiries", "version")
