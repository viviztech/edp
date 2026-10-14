"""L02.3 assessment eligibility and certificates."""

import sqlalchemy as sa
from alembic import op

revision = "d4c0f6a8b123"
down_revision = "c3b9e5f7a012"
branch_labels = None
depends_on = None


def record_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.execute("""
        INSERT INTO permissions (code)
        VALUES ('certificate.manage'), ('certificate.issue')
        ON CONFLICT DO NOTHING;
        INSERT INTO role_permissions (role_id, permission_code)
        SELECT roles.id, permissions.code
        FROM roles CROSS JOIN permissions
        WHERE roles.name IN ('Super Admin','Program Director')
          AND permissions.code IN ('certificate.manage','certificate.issue')
        ON CONFLICT DO NOTHING;
        INSERT INTO role_permissions (role_id, permission_code)
        SELECT roles.id, 'certificate.manage'
        FROM roles
        WHERE roles.name = 'Program Manager'
        ON CONFLICT DO NOTHING;
    """)

    op.create_table(
        "certificate_templates",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("title_en", sa.String(200), nullable=False),
        sa.Column("title_ta", sa.String(200), nullable=False),
        sa.Column("statement_en", sa.Text(), nullable=False),
        sa.Column("statement_ta", sa.Text(), nullable=False),
        sa.Column("issuer_name", sa.String(200), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        *record_columns(),
        sa.ForeignKeyConstraint(
            ["course_id", "organization_id"],
            ["courses.id", "courses.organization_id"],
            name="fk_certificate_template_course_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code"),
        sa.UniqueConstraint("id", "course_id", "organization_id"),
        sa.CheckConstraint(
            "state IN ('draft','published','retired')", name="certificate_template_state"
        ),
        sa.CheckConstraint("version > 0", name="certificate_template_version"),
        sa.CheckConstraint(
            "(state = 'draft' AND published_at IS NULL) OR "
            "(state IN ('published','retired') AND published_at IS NOT NULL)",
            name="certificate_template_publication_evidence",
        ),
    )
    op.create_index(
        "ix_certificate_templates_organization_id",
        "certificate_templates",
        ["organization_id"],
    )
    op.create_index("ix_certificate_templates_course_id", "certificate_templates", ["course_id"])
    op.create_index(
        "uq_certificate_template_published_course",
        "certificate_templates",
        ["course_id"],
        unique=True,
        postgresql_where=sa.text("state = 'published'"),
    )

    op.create_table(
        "certificates",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("course_enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("issued_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("verification_code", sa.String(48), nullable=False),
        sa.Column("recipient_name", sa.String(200), nullable=False),
        sa.Column("course_title_en", sa.String(200), nullable=False),
        sa.Column("course_title_ta", sa.String(200), nullable=False),
        sa.Column("certificate_title_en", sa.String(200), nullable=False),
        sa.Column("certificate_title_ta", sa.String(200), nullable=False),
        sa.Column("statement_en", sa.Text(), nullable=False),
        sa.Column("statement_ta", sa.Text(), nullable=False),
        sa.Column("issuer_name", sa.String(200), nullable=False),
        sa.Column("template_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoke_reason", sa.String(500), nullable=True),
        *record_columns(),
        sa.ForeignKeyConstraint(
            ["course_enrollment_id", "course_id", "organization_id"],
            [
                "course_enrollments.id",
                "course_enrollments.course_id",
                "course_enrollments.organization_id",
            ],
            name="fk_certificate_enrollment_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["template_id", "course_id", "organization_id"],
            [
                "certificate_templates.id",
                "certificate_templates.course_id",
                "certificate_templates.organization_id",
            ],
            name="fk_certificate_template_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["issued_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("status IN ('valid','revoked')", name="certificate_status"),
        sa.CheckConstraint("version > 0", name="certificate_version"),
        sa.CheckConstraint("template_version > 0", name="certificate_template_version_snapshot"),
        sa.CheckConstraint(
            "(status = 'valid' AND revoked_at IS NULL AND revoke_reason IS NULL) OR "
            "(status = 'revoked' AND revoked_at IS NOT NULL AND revoke_reason IS NOT NULL)",
            name="certificate_revocation_evidence",
        ),
    )
    for column in (
        "organization_id",
        "course_id",
        "course_enrollment_id",
        "template_id",
        "issued_by_user_id",
    ):
        op.create_index(f"ix_certificates_{column}", "certificates", [column])
    op.create_index(
        "ix_certificates_verification_code",
        "certificates",
        ["verification_code"],
        unique=True,
    )
    op.create_index(
        "uq_certificate_valid_enrollment",
        "certificates",
        ["course_enrollment_id"],
        unique=True,
        postgresql_where=sa.text("status = 'valid'"),
    )

    op.execute("""
        CREATE FUNCTION protect_certificate_template() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'certificate template evidence cannot be deleted';
          END IF;
          IF OLD.state <> 'draft'
             OR NEW.state <> 'published'
             OR NEW.version <> OLD.version + 1
             OR NEW.published_at IS NULL
             OR ROW(NEW.organization_id, NEW.course_id, NEW.code, NEW.title_en,
                    NEW.title_ta, NEW.statement_en, NEW.statement_ta, NEW.issuer_name)
                IS DISTINCT FROM
                ROW(OLD.organization_id, OLD.course_id, OLD.code, OLD.title_en,
                    OLD.title_ta, OLD.statement_en, OLD.statement_ta, OLD.issuer_name) THEN
            RAISE EXCEPTION 'certificate template evidence is immutable';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_certificate_template_protect
        BEFORE UPDATE OR DELETE ON certificate_templates
        FOR EACH ROW EXECUTE FUNCTION protect_certificate_template();

        CREATE FUNCTION protect_certificate_evidence() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'certificate evidence cannot be deleted';
          END IF;
          IF OLD.status <> 'valid'
             OR NEW.status <> 'revoked'
             OR NEW.version <> OLD.version + 1
             OR NEW.revoked_at IS NULL
             OR NEW.revoke_reason IS NULL
             OR ROW(NEW.organization_id, NEW.course_id, NEW.course_enrollment_id,
                    NEW.template_id, NEW.issued_by_user_id, NEW.verification_code,
                    NEW.recipient_name, NEW.course_title_en, NEW.course_title_ta,
                    NEW.certificate_title_en, NEW.certificate_title_ta,
                    NEW.statement_en, NEW.statement_ta, NEW.issuer_name,
                    NEW.template_version, NEW.issued_at)
                IS DISTINCT FROM
                ROW(OLD.organization_id, OLD.course_id, OLD.course_enrollment_id,
                    OLD.template_id, OLD.issued_by_user_id, OLD.verification_code,
                    OLD.recipient_name, OLD.course_title_en, OLD.course_title_ta,
                    OLD.certificate_title_en, OLD.certificate_title_ta,
                    OLD.statement_en, OLD.statement_ta, OLD.issuer_name,
                    OLD.template_version, OLD.issued_at) THEN
            RAISE EXCEPTION 'certificate evidence is immutable';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_certificate_protect
        BEFORE UPDATE OR DELETE ON certificates
        FOR EACH ROW EXECUTE FUNCTION protect_certificate_evidence();
    """)


def downgrade() -> None:
    op.execute("""
        DROP TRIGGER trg_certificate_protect ON certificates;
        DROP FUNCTION protect_certificate_evidence;
        DROP TRIGGER trg_certificate_template_protect ON certificate_templates;
        DROP FUNCTION protect_certificate_template;
    """)
    op.drop_table("certificates")
    op.drop_table("certificate_templates")
    op.execute("""
        DELETE FROM role_permissions
        WHERE permission_code IN ('certificate.manage','certificate.issue');
        DELETE FROM permissions
        WHERE code IN ('certificate.manage','certificate.issue');
    """)
