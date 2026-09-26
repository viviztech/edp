"""Harden L01.2 course progress transitions without data loss."""

from alembic import op

revision = "9a8cc5a7c32f"
down_revision = "8f7bf4f6b21e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION protect_course_completion_rule() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF (OLD.state <> 'draft' OR NEW.state <> 'draft')
             AND (NEW.completion_rule IS DISTINCT FROM OLD.completion_rule
                  OR NEW.minimum_lessons IS DISTINCT FROM OLD.minimum_lessons) THEN
            RAISE EXCEPTION 'published completion rule is immutable';
          END IF;
          RETURN NEW;
        END $$;

        CREATE FUNCTION protect_course_enrollment_progress() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF NEW.id IS DISTINCT FROM OLD.id
             OR NEW.organization_id IS DISTINCT FROM OLD.organization_id
             OR NEW.enrollment_id IS DISTINCT FROM OLD.enrollment_id
             OR NEW.course_id IS DISTINCT FROM OLD.course_id
             OR NEW.started_at IS DISTINCT FROM OLD.started_at
             OR OLD.status = 'completed'
             OR NEW.version <> OLD.version + 1 THEN
            RAISE EXCEPTION 'invalid course enrollment progress transition';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_course_enrollment_progress
        BEFORE UPDATE ON course_enrollments
        FOR EACH ROW EXECUTE FUNCTION protect_course_enrollment_progress();
    """)


def downgrade() -> None:
    op.execute("""
        DROP TRIGGER trg_course_enrollment_progress ON course_enrollments;
        DROP FUNCTION protect_course_enrollment_progress;
        CREATE OR REPLACE FUNCTION protect_course_completion_rule() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.state <> 'draft'
             AND (NEW.completion_rule IS DISTINCT FROM OLD.completion_rule
                  OR NEW.minimum_lessons IS DISTINCT FROM OLD.minimum_lessons) THEN
            RAISE EXCEPTION 'published completion rule is immutable';
          END IF;
          RETURN NEW;
        END $$;
    """)
