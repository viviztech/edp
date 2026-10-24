"""Typed learning files and immutable assignment/material evidence."""

import sqlalchemy as sa
from alembic import op

revision = "k6a2b8c4d901"
down_revision = "j5f1a7b3c890"
branch_labels = None
depends_on = None

POLICY_GUARD_BEFORE = "OR NOT (policy.state = 'published' OR ("
POLICY_GUARD_AFTER = """OR NOT (policy.state = 'published' OR (
    NEW.purpose = 'assignment_submission' AND policy.state = 'retired'
    AND policy.published_at IS NOT NULL AND EXISTS (
      SELECT 1 FROM assignment_file_rules r JOIN courses c ON c.id = r.course_id
      JOIN course_enrollments ce ON ce.course_id = c.id
      JOIN enrollments e ON e.id = ce.enrollment_id
      JOIN participants p ON p.id = e.participant_id
      WHERE r.policy_id = NEW.policy_id AND c.organization_id = NEW.organization_id
        AND p.person_id = NEW.owner_person_id AND c.state = 'published'
        AND c.published_at >= policy.published_at
    )) OR ("""


def replace_policy_guard(before: str, after: str) -> None:
    definition = op.get_bind().scalar(
        sa.text("SELECT pg_get_functiondef('file_object_guard()'::regprocedure)")
    )
    if not isinstance(definition, str) or definition.count(before) != 1:
        raise RuntimeError("Unexpected predecessor file lifecycle guard")
    op.execute(sa.text(definition.replace(before, after)))


LEARNING_GUARDS = """
CREATE FUNCTION protect_assignment_file_rule() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE definition learning_assignments; parent courses; policy file_policies;
BEGIN
  IF TG_OP = 'DELETE' THEN
    SELECT * INTO parent FROM courses WHERE id = OLD.course_id FOR UPDATE;
    IF parent.state <> 'draft' THEN RAISE EXCEPTION 'published file rules immutable'; END IF;
    RETURN OLD;
  END IF;
  SELECT * INTO definition FROM learning_assignments WHERE id = NEW.assignment_id;
  SELECT * INTO parent FROM courses WHERE id = definition.course_id FOR UPDATE;
  SELECT * INTO policy FROM file_policies WHERE id = NEW.policy_id;
  IF parent.state <> 'draft' OR policy.state <> 'published'
      OR NEW.maximum_files > policy.max_files THEN
    RAISE EXCEPTION 'file rules require draft course and published policy'; END IF;
  IF TG_OP = 'INSERT' AND NEW.version <> 1 THEN
    RAISE EXCEPTION 'invalid initial file rule version'; END IF;
  IF TG_OP = 'UPDATE' AND (NEW.version <> OLD.version + 1 OR
      (to_jsonb(NEW) - ARRAY['policy_id','minimum_files','maximum_files','version'])
      IS DISTINCT FROM
      (to_jsonb(OLD) - ARRAY['policy_id','minimum_files','maximum_files','version'])) THEN
    RAISE EXCEPTION 'file rule identity immutable'; END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_assignment_file_rule BEFORE INSERT OR UPDATE OR DELETE
  ON assignment_file_rules FOR EACH ROW EXECUTE FUNCTION protect_assignment_file_rule();

CREATE FUNCTION protect_assignment_file() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE parent courses; definition learning_assignments; policy file_policies;
DECLARE rule assignment_file_rules; object file_objects; submission assignment_submissions;
DECLARE owner_id uuid; revision_number integer; active_count integer;
BEGIN
  IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'file binding metadata is retained'; END IF;
  PERFORM 1 FROM course_enrollments WHERE id = NEW.course_enrollment_id FOR UPDATE;
  SELECT p.person_id INTO owner_id FROM course_enrollments ce
    JOIN enrollments e ON e.id = ce.enrollment_id
    JOIN participants p ON p.id = e.participant_id WHERE ce.id = NEW.course_enrollment_id;
  SELECT * INTO definition FROM learning_assignments WHERE id = NEW.assignment_id;
  SELECT * INTO parent FROM courses WHERE id = NEW.course_id;
  SELECT * INTO rule FROM assignment_file_rules WHERE assignment_id = NEW.assignment_id;
  SELECT * INTO object FROM file_objects WHERE id = NEW.file_id;
  SELECT * INTO policy FROM file_policies WHERE id = rule.policy_id;
  IF owner_id IS DISTINCT FROM NEW.owner_person_id OR rule.id IS NULL
      OR object.policy_id <> rule.policy_id OR parent.state <> 'published'
      OR parent.published_at < policy.published_at THEN
    RAISE EXCEPTION 'assignment file requires exact owner and frozen rule'; END IF;
  IF TG_OP = 'INSERT' THEN
    SELECT COALESCE(MAX(revision),0)+1 INTO revision_number FROM assignment_submissions
      WHERE course_enrollment_id = NEW.course_enrollment_id
        AND assignment_id = NEW.assignment_id;
    SELECT count(*) INTO active_count FROM assignment_files
      WHERE course_enrollment_id = NEW.course_enrollment_id
        AND assignment_id = NEW.assignment_id AND target_revision = NEW.target_revision
        AND state = 'active';
    IF NEW.state <> 'active' OR NEW.version <> 1 OR NEW.target_revision <> revision_number
        OR revision_number > definition.max_submissions
        OR active_count >= LEAST(rule.maximum_files,policy.max_files) THEN
      RAISE EXCEPTION 'invalid assignment file intent'; END IF;
    IF revision_number > 1 AND NOT EXISTS (SELECT 1 FROM assignment_submissions s
        JOIN assignment_grades g ON g.submission_id = s.id
        WHERE s.course_enrollment_id = NEW.course_enrollment_id
          AND s.assignment_id = NEW.assignment_id AND s.revision = revision_number - 1) THEN
      RAISE EXCEPTION 'previous revision awaits review'; END IF;
  ELSE
    IF OLD.state <> 'active' OR NEW.state NOT IN ('removed','submitted')
        OR NEW.version <> OLD.version + 1 OR
        (to_jsonb(NEW) - ARRAY['state','version','submission_id','frozen_file_version',
          'frozen_storage_version','frozen_sha256','frozen_byte_size','frozen_at'])
        IS DISTINCT FROM
        (to_jsonb(OLD) - ARRAY['state','version','submission_id','frozen_file_version',
          'frozen_storage_version','frozen_sha256','frozen_byte_size','frozen_at']) THEN
      RAISE EXCEPTION 'assignment file identity and submitted evidence immutable'; END IF;
    IF NEW.state = 'submitted' THEN
      SELECT * INTO submission FROM assignment_submissions WHERE id = NEW.submission_id;
      IF submission.revision <> NEW.target_revision OR NOT object.evidence_frozen
          OR object.state <> 'clean' OR object.retention_until <= CURRENT_TIMESTAMP
          OR NEW.frozen_file_version <> object.version
          OR NEW.frozen_storage_version <> object.storage_version
          OR NEW.frozen_sha256 <> object.stored_sha256
          OR NEW.frozen_byte_size <> object.stored_byte_size THEN
        RAISE EXCEPTION 'submission requires exact clean frozen bytes'; END IF;
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_assignment_file BEFORE INSERT OR UPDATE OR DELETE ON assignment_files
  FOR EACH ROW EXECUTE FUNCTION protect_assignment_file();

CREATE FUNCTION validate_learning_submission_files() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE rule assignment_file_rules; total integer;
BEGIN
  SELECT * INTO rule FROM assignment_file_rules WHERE assignment_id = NEW.assignment_id;
  SELECT count(*) INTO total FROM assignment_files WHERE submission_id = NEW.id
    AND state = 'submitted';
  IF rule.id IS NOT NULL AND (total < rule.minimum_files OR total > rule.maximum_files) THEN
    RAISE EXCEPTION 'assignment submission file count invalid'; END IF;
  RETURN NEW;
END $$;
CREATE CONSTRAINT TRIGGER trg_learning_submission_files AFTER INSERT ON assignment_submissions
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
  EXECUTE FUNCTION validate_learning_submission_files();

CREATE FUNCTION validate_retired_learning_pin() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM file_policies WHERE id = NEW.policy_id AND state = 'retired')
      AND NOT EXISTS (SELECT 1 FROM assignment_files d
        JOIN assignment_file_rules r ON r.assignment_id = d.assignment_id
        JOIN courses c ON c.id = d.course_id
        JOIN file_policies p ON p.id = r.policy_id
        WHERE d.file_id = NEW.id AND d.id = NEW.resource_id
          AND d.organization_id = NEW.organization_id
          AND d.owner_person_id = NEW.owner_person_id AND r.policy_id = NEW.policy_id
          AND c.state = 'published' AND c.published_at >= p.published_at) THEN
    RAISE EXCEPTION 'retired policy requires typed published learning pin'; END IF;
  RETURN NEW;
END $$;
CREATE CONSTRAINT TRIGGER trg_retired_learning_pin AFTER INSERT ON file_objects
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (NEW.purpose = 'assignment_submission')
  EXECUTE FUNCTION validate_retired_learning_pin();

CREATE FUNCTION protect_material_file() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE parent courses; material lesson_materials; object file_objects;
BEGIN
  IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'material file metadata retained'; END IF;
  SELECT * INTO material FROM lesson_materials WHERE id = NEW.material_id;
  SELECT * INTO parent FROM courses WHERE id = NEW.course_id FOR UPDATE;
  SELECT * INTO object FROM file_objects WHERE id = NEW.file_id;
  IF parent.state <> 'draft' OR material.kind <> 'document'
      OR material.provider_key <> 'shared-file:' || material.id::text THEN
    RAISE EXCEPTION 'material file requires a typed draft material'; END IF;
  IF TG_OP = 'INSERT' THEN
    IF NEW.frozen_at IS NOT NULL THEN RAISE EXCEPTION 'material starts unfrozen'; END IF;
  ELSE
    IF OLD.frozen_at IS NOT NULL OR NEW.frozen_at IS NULL OR
        (to_jsonb(NEW) - ARRAY['frozen_file_version','frozen_storage_version',
          'frozen_sha256','frozen_byte_size','frozen_at']) IS DISTINCT FROM
        (to_jsonb(OLD) - ARRAY['frozen_file_version','frozen_storage_version',
          'frozen_sha256','frozen_byte_size','frozen_at']) THEN
      RAISE EXCEPTION 'material binding identity immutable'; END IF;
    IF object.state <> 'clean' OR NOT object.evidence_frozen
        OR object.retention_until <= CURRENT_TIMESTAMP
        OR NEW.frozen_file_version <> object.version
        OR NEW.frozen_storage_version <> object.storage_version
        OR NEW.frozen_sha256 <> object.stored_sha256
        OR NEW.frozen_byte_size <> object.stored_byte_size THEN
      RAISE EXCEPTION 'material publication requires exact clean frozen bytes'; END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_material_file BEFORE INSERT OR UPDATE OR DELETE ON lesson_material_files
  FOR EACH ROW EXECUTE FUNCTION protect_material_file();

CREATE FUNCTION validate_course_file_publication() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.state = 'published' AND OLD.state = 'draft' THEN
    IF EXISTS (SELECT 1 FROM lesson_materials m LEFT JOIN lesson_material_files b
        ON b.material_id = m.id LEFT JOIN file_objects f ON f.id = b.file_id
        WHERE m.course_id = NEW.id AND m.provider_key LIKE 'shared-file:%'
          AND (b.frozen_at IS NULL OR f.state <> 'clean' OR NOT f.evidence_frozen
            OR f.retention_until <= CURRENT_TIMESTAMP
            OR b.frozen_storage_version <> f.storage_version
            OR b.frozen_sha256 <> f.stored_sha256 OR b.frozen_byte_size <> f.stored_byte_size)) THEN
      RAISE EXCEPTION 'course material lacks frozen file evidence'; END IF;
    IF EXISTS (SELECT 1 FROM assignment_file_rules r JOIN file_policies p ON p.id = r.policy_id
        WHERE r.course_id = NEW.id AND (p.state <> 'published'
          OR p.published_at > NEW.published_at OR r.maximum_files > p.max_files)) THEN
      RAISE EXCEPTION 'course file rules lack published policy'; END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_course_file_publication BEFORE UPDATE ON courses
  FOR EACH ROW EXECUTE FUNCTION validate_course_file_publication();
"""


def upgrade():
    op.create_unique_constraint(
        "uq_submission_file_owner_scope",
        "assignment_submissions",
        ["id", "course_enrollment_id", "assignment_id", "course_id", "organization_id"],
    )
    op.create_unique_constraint(
        "uq_material_file_scope", "lesson_materials", ["id", "course_id", "organization_id"]
    )
    op.create_table(
        "assignment_file_rules",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("minimum_files", sa.Integer(), nullable=False),
        sa.Column("maximum_files", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "purpose = 'assignment_submission'", name="assignment_file_rule_purpose"
        ),
        sa.CheckConstraint(
            "minimum_files >= 0 AND maximum_files BETWEEN 1 AND 100 "
            "AND minimum_files <= maximum_files",
            name="assignment_file_rule_count",
        ),
        sa.CheckConstraint("version > 0", name="assignment_file_rule_version"),
        sa.ForeignKeyConstraint(
            ["assignment_id", "course_id", "organization_id"],
            [
                "learning_assignments.id",
                "learning_assignments.course_id",
                "learning_assignments.organization_id",
            ],
            name="fk_assignment_file_rule_definition",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["policy_id", "organization_id", "purpose"],
            ["file_policies.id", "file_policies.organization_id", "file_policies.purpose"],
            name="fk_assignment_file_rule_policy",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assignment_id"),
    )
    op.create_table(
        "assignment_files",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("course_enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("owner_person_id", sa.Uuid(), nullable=False),
        sa.Column("client_request_id", sa.Uuid(), nullable=False),
        sa.Column("file_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("target_revision", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("submission_id", sa.Uuid(), nullable=True),
        sa.Column("frozen_file_version", sa.Integer(), nullable=True),
        sa.Column("frozen_storage_version", sa.String(length=1024), nullable=True),
        sa.Column("frozen_sha256", sa.String(length=64), nullable=True),
        sa.Column("frozen_byte_size", sa.Integer(), nullable=True),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(state = 'submitted' AND submission_id IS NOT NULL "
            "AND frozen_file_version IS NOT NULL AND frozen_storage_version IS NOT NULL "
            "AND frozen_sha256 IS NOT NULL AND frozen_byte_size IS NOT NULL "
            "AND frozen_byte_size > 0 AND frozen_at IS NOT NULL) "
            "OR (state <> 'submitted' AND submission_id IS NULL AND frozen_file_version IS NULL "
            "AND frozen_storage_version IS NULL AND frozen_sha256 IS NULL "
            "AND frozen_byte_size IS NULL AND frozen_at IS NULL)",
            name="assignment_file_frozen_evidence",
        ),
        sa.CheckConstraint("purpose = 'assignment_submission'", name="assignment_file_purpose"),
        sa.CheckConstraint(
            "state IN ('active','removed','submitted') AND version > 0 "
            "AND target_revision BETWEEN 1 AND 10",
            name="assignment_file_state",
        ),
        sa.ForeignKeyConstraint(
            ["assignment_id", "course_id", "organization_id"],
            [
                "learning_assignments.id",
                "learning_assignments.course_id",
                "learning_assignments.organization_id",
            ],
            name="fk_assignment_file_definition",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["course_enrollment_id", "course_id", "organization_id"],
            [
                "course_enrollments.id",
                "course_enrollments.course_id",
                "course_enrollments.organization_id",
            ],
            name="fk_assignment_file_enrollment",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["file_id", "organization_id", "owner_person_id", "purpose", "id"],
            [
                "file_objects.id",
                "file_objects.organization_id",
                "file_objects.owner_person_id",
                "file_objects.purpose",
                "file_objects.resource_id",
            ],
            name="fk_assignment_file_object",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            [
                "submission_id",
                "course_enrollment_id",
                "assignment_id",
                "course_id",
                "organization_id",
            ],
            [
                "assignment_submissions.id",
                "assignment_submissions.course_enrollment_id",
                "assignment_submissions.assignment_id",
                "assignment_submissions.course_id",
                "assignment_submissions.organization_id",
            ],
            name="fk_assignment_file_submission",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_id"),
        sa.UniqueConstraint("organization_id", "client_request_id"),
    )
    op.create_table(
        "lesson_material_files",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("material_id", sa.Uuid(), nullable=False),
        sa.Column("owner_person_id", sa.Uuid(), nullable=False),
        sa.Column("client_request_id", sa.Uuid(), nullable=False),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.Column("file_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("frozen_file_version", sa.Integer(), nullable=True),
        sa.Column("frozen_storage_version", sa.String(length=1024), nullable=True),
        sa.Column("frozen_sha256", sa.String(length=64), nullable=True),
        sa.Column("frozen_byte_size", sa.Integer(), nullable=True),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("purpose = 'lms_material'", name="material_file_purpose"),
        sa.CheckConstraint(
            "(frozen_at IS NULL AND frozen_file_version IS NULL AND frozen_storage_version IS NULL "
            "AND frozen_sha256 IS NULL AND frozen_byte_size IS NULL) OR (frozen_at IS NOT NULL "
            "AND frozen_file_version IS NOT NULL AND frozen_file_version > 0 "
            "AND frozen_storage_version IS NOT NULL AND frozen_sha256 IS NOT NULL "
            "AND frozen_byte_size IS NOT NULL AND frozen_byte_size > 0)",
            name="material_file_frozen_evidence",
        ),
        sa.ForeignKeyConstraint(
            ["file_id", "organization_id", "owner_person_id", "purpose", "material_id"],
            [
                "file_objects.id",
                "file_objects.organization_id",
                "file_objects.owner_person_id",
                "file_objects.purpose",
                "file_objects.resource_id",
            ],
            name="fk_material_file_object",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["material_id", "course_id", "organization_id"],
            [
                "lesson_materials.id",
                "lesson_materials.course_id",
                "lesson_materials.organization_id",
            ],
            name="fk_material_file_material",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_id"),
        sa.UniqueConstraint("material_id"),
        sa.UniqueConstraint("organization_id", "client_request_id"),
    )
    op.execute(LEARNING_GUARDS)
    replace_policy_guard(POLICY_GUARD_BEFORE, POLICY_GUARD_AFTER)


def downgrade():
    replace_policy_guard(POLICY_GUARD_AFTER, POLICY_GUARD_BEFORE)
    op.execute("""
    DROP TRIGGER trg_course_file_publication ON courses;
    DROP FUNCTION validate_course_file_publication();
    DROP TRIGGER trg_material_file ON lesson_material_files;
    DROP FUNCTION protect_material_file();
    DROP TRIGGER trg_retired_learning_pin ON file_objects;
    DROP FUNCTION validate_retired_learning_pin();
    DROP TRIGGER trg_learning_submission_files ON assignment_submissions;
    DROP FUNCTION validate_learning_submission_files();
    DROP TRIGGER trg_assignment_file ON assignment_files;
    DROP FUNCTION protect_assignment_file();
    DROP TRIGGER trg_assignment_file_rule ON assignment_file_rules;
    DROP FUNCTION protect_assignment_file_rule();
    """)
    op.drop_table("lesson_material_files")
    op.drop_table("assignment_files")
    op.drop_table("assignment_file_rules")
    op.drop_constraint("uq_material_file_scope", "lesson_materials", type_="unique")
    op.drop_constraint("uq_submission_file_owner_scope", "assignment_submissions", type_="unique")
