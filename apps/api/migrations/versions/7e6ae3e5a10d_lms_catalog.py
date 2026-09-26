"""L01.1 learning catalog and enrollment access."""

# ruff: noqa: E501

import sqlalchemy as sa
from alembic import op

revision = "7e6ae3e5a10d"
down_revision = "6d59d2d4f99c"
branch_labels = None
depends_on = None


def record_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    for code in (
        "lms.course.view",
        "lms.course.manage",
        "lms.course.publish",
        "lms.course.assign",
        "lms.learn",
    ):
        op.execute(
            sa.text(
                "INSERT INTO permissions (code) VALUES (:code) ON CONFLICT DO NOTHING"
            ).bindparams(code=code)
        )
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_code)
        SELECT roles.id, permissions.code
        FROM roles CROSS JOIN permissions
        WHERE roles.name IN ('Super Admin', 'Program Director', 'Program Manager')
          AND permissions.code IN (
            'lms.course.view','lms.course.manage','lms.course.publish','lms.course.assign'
          )
        ON CONFLICT DO NOTHING
    """)
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_code)
        SELECT roles.id, permissions.code
        FROM roles CROSS JOIN permissions
        WHERE roles.name = 'Participant' AND permissions.code = 'lms.learn'
        ON CONFLICT DO NOTHING
    """)

    op.create_table(
        "courses",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("title_en", sa.String(200), nullable=False),
        sa.Column("title_ta", sa.String(200), nullable=False),
        sa.Column("description_en", sa.Text(), nullable=False),
        sa.Column("description_ta", sa.Text(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        *record_columns(),
        sa.CheckConstraint(
            "(state = 'draft' AND published_at IS NULL) OR "
            "(state IN ('published','archived') AND published_at IS NOT NULL)",
            name="course_publication_evidence",
        ),
        sa.CheckConstraint("state IN ('draft','published','archived')", name="course_state"),
        sa.CheckConstraint("version > 0", name="course_version"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code"),
        sa.UniqueConstraint("id", "organization_id"),
    )
    op.create_index("ix_courses_organization_id", "courses", ["organization_id"])
    op.create_index("ix_course_scope_state", "courses", ["organization_id", "state", "id"])

    op.create_table(
        "course_modules",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title_en", sa.String(200), nullable=False),
        sa.Column("title_ta", sa.String(200), nullable=False),
        *record_columns(),
        sa.CheckConstraint("position > 0", name="course_module_position"),
        sa.ForeignKeyConstraint(
            ["course_id", "organization_id"],
            ["courses.id", "courses.organization_id"],
            name="fk_course_module_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id", "position"),
        sa.UniqueConstraint("id", "course_id", "organization_id"),
    )
    op.create_index("ix_course_modules_organization_id", "course_modules", ["organization_id"])
    op.create_index("ix_course_modules_course_id", "course_modules", ["course_id"])

    op.create_table(
        "lessons",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("module_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title_en", sa.String(200), nullable=False),
        sa.Column("title_ta", sa.String(200), nullable=False),
        sa.Column("body_en", sa.Text(), nullable=False),
        sa.Column("body_ta", sa.Text(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        *record_columns(),
        sa.CheckConstraint(
            "duration_minutes IS NULL OR duration_minutes > 0", name="lesson_duration"
        ),
        sa.CheckConstraint("position > 0", name="lesson_position"),
        sa.ForeignKeyConstraint(
            ["module_id", "course_id", "organization_id"],
            ["course_modules.id", "course_modules.course_id", "course_modules.organization_id"],
            name="fk_lesson_module_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("module_id", "position"),
        sa.UniqueConstraint("id", "course_id", "organization_id"),
    )
    op.create_index("ix_lessons_organization_id", "lessons", ["organization_id"])
    op.create_index("ix_lessons_course_id", "lessons", ["course_id"])
    op.create_index("ix_lessons_module_id", "lessons", ["module_id"])

    op.create_table(
        "lesson_materials",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("lesson_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("label_en", sa.String(200), nullable=False),
        sa.Column("label_ta", sa.String(200), nullable=False),
        sa.Column("provider_key", sa.String(500), nullable=False),
        sa.Column("is_private", sa.Boolean(), nullable=False),
        *record_columns(),
        sa.CheckConstraint("is_private = true", name="lesson_material_private"),
        sa.CheckConstraint("kind IN ('video','document','link')", name="lesson_material_kind"),
        sa.CheckConstraint("position > 0", name="lesson_material_position"),
        sa.ForeignKeyConstraint(
            ["lesson_id", "course_id", "organization_id"],
            ["lessons.id", "lessons.course_id", "lessons.organization_id"],
            name="fk_lesson_material_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lesson_id", "position"),
    )
    op.create_index("ix_lesson_materials_organization_id", "lesson_materials", ["organization_id"])
    op.create_index("ix_lesson_materials_course_id", "lesson_materials", ["course_id"])
    op.create_index("ix_lesson_materials_lesson_id", "lesson_materials", ["lesson_id"])

    op.create_table(
        "cohort_courses",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("cohort_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        *record_columns(),
        sa.CheckConstraint("position > 0", name="cohort_course_position"),
        sa.ForeignKeyConstraint(
            ["cohort_id", "organization_id"],
            ["cohorts.id", "cohorts.organization_id"],
            name="fk_cohort_course_cohort_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["course_id", "organization_id"],
            ["courses.id", "courses.organization_id"],
            name="fk_cohort_course_course_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cohort_id", "course_id"),
        sa.UniqueConstraint("cohort_id", "position"),
        sa.UniqueConstraint("id", "organization_id"),
    )
    op.create_index("ix_cohort_courses_organization_id", "cohort_courses", ["organization_id"])
    op.create_index("ix_cohort_courses_cohort_id", "cohort_courses", ["cohort_id"])
    op.create_index("ix_cohort_courses_course_id", "cohort_courses", ["course_id"])
    op.create_index("ix_cohort_course_order", "cohort_courses", ["cohort_id", "position", "id"])

    op.create_table(
        "course_enrollments",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        *record_columns(),
        sa.CheckConstraint(
            "(status = 'in_progress' AND completed_at IS NULL) OR "
            "(status = 'completed' AND completed_at IS NOT NULL)",
            name="course_enrollment_completion_evidence",
        ),
        sa.CheckConstraint(
            "status IN ('in_progress','completed')", name="course_enrollment_status"
        ),
        sa.CheckConstraint("version > 0", name="course_enrollment_version"),
        sa.ForeignKeyConstraint(
            ["enrollment_id", "organization_id"],
            ["enrollments.id", "enrollments.organization_id"],
            name="fk_course_enrollment_enrollment_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["course_id", "organization_id"],
            ["courses.id", "courses.organization_id"],
            name="fk_course_enrollment_course_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("enrollment_id", "course_id"),
        sa.UniqueConstraint("id", "organization_id"),
    )
    op.create_index(
        "ix_course_enrollments_organization_id", "course_enrollments", ["organization_id"]
    )
    op.create_index("ix_course_enrollments_enrollment_id", "course_enrollments", ["enrollment_id"])
    op.create_index("ix_course_enrollments_course_id", "course_enrollments", ["course_id"])

    op.execute("""
        CREATE FUNCTION protect_published_course_structure() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE target_course uuid;
        DECLARE course_state text;
        BEGIN
          target_course := CASE WHEN TG_OP = 'DELETE' THEN OLD.course_id ELSE NEW.course_id END;
          SELECT state INTO course_state FROM courses WHERE id = target_course;
          IF course_state IS DISTINCT FROM 'draft' THEN
            RAISE EXCEPTION 'published course structure is immutable';
          END IF;
          IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_course_module_draft_only
        BEFORE INSERT OR UPDATE OR DELETE ON course_modules
        FOR EACH ROW EXECUTE FUNCTION protect_published_course_structure();
        CREATE TRIGGER trg_lesson_draft_only
        BEFORE INSERT OR UPDATE OR DELETE ON lessons
        FOR EACH ROW EXECUTE FUNCTION protect_published_course_structure();
        CREATE TRIGGER trg_lesson_material_draft_only
        BEFORE INSERT OR UPDATE OR DELETE ON lesson_materials
        FOR EACH ROW EXECUTE FUNCTION protect_published_course_structure();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_lesson_material_draft_only ON lesson_materials")
    op.execute("DROP TRIGGER trg_lesson_draft_only ON lessons")
    op.execute("DROP TRIGGER trg_course_module_draft_only ON course_modules")
    op.execute("DROP FUNCTION protect_published_course_structure")
    for table in (
        "course_enrollments",
        "cohort_courses",
        "lesson_materials",
        "lessons",
        "course_modules",
        "courses",
    ):
        op.drop_table(table)
    op.execute("""
        DELETE FROM role_permissions
        WHERE permission_code IN (
          'lms.course.view','lms.course.manage','lms.course.publish','lms.course.assign','lms.learn'
        )
    """)
    op.execute("""
        DELETE FROM permissions
        WHERE code IN (
          'lms.course.view','lms.course.manage','lms.course.publish','lms.course.assign','lms.learn'
        )
    """)
