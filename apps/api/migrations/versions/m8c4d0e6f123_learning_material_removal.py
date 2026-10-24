"""Retain removed draft material evidence while allowing explicit replacement.

Revision ID: m8c4d0e6f123
Revises: l7b3c9d5e012
"""

import sqlalchemy as sa
from alembic import op

revision = "m8c4d0e6f123"
down_revision = "l7b3c9d5e012"
branch_labels = None
depends_on = None

OLD_GUARD = """
CREATE OR REPLACE FUNCTION protect_material_file() RETURNS trigger LANGUAGE plpgsql AS $$
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
"""

NEW_GUARD = """
CREATE OR REPLACE FUNCTION protect_material_file() RETURNS trigger LANGUAGE plpgsql AS $$
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
    IF NEW.state <> 'active' OR NEW.version <> 1 OR NEW.frozen_at IS NOT NULL THEN
      RAISE EXCEPTION 'material starts active and unfrozen'; END IF;
  ELSE
    IF OLD.state <> 'active' OR OLD.frozen_at IS NOT NULL OR NEW.version <> OLD.version + 1 OR
        (to_jsonb(NEW) - ARRAY['state','version','frozen_file_version','frozen_storage_version',
          'frozen_sha256','frozen_byte_size','frozen_at']) IS DISTINCT FROM
        (to_jsonb(OLD) - ARRAY['state','version','frozen_file_version','frozen_storage_version',
          'frozen_sha256','frozen_byte_size','frozen_at']) THEN
      RAISE EXCEPTION 'material binding identity and published evidence immutable'; END IF;
    IF NEW.state = 'removed' THEN
      IF NEW.frozen_at IS NOT NULL THEN
        RAISE EXCEPTION 'removed material cannot have published evidence'; END IF;
    ELSIF NEW.state = 'active' AND NEW.frozen_at IS NOT NULL THEN
      IF object.state <> 'clean' OR NOT object.evidence_frozen
          OR object.retention_until <= CURRENT_TIMESTAMP
          OR NEW.frozen_file_version <> object.version
          OR NEW.frozen_storage_version <> object.storage_version
          OR NEW.frozen_sha256 <> object.stored_sha256
          OR NEW.frozen_byte_size <> object.stored_byte_size THEN
        RAISE EXCEPTION 'material publication requires exact clean frozen bytes'; END IF;
    ELSE
      RAISE EXCEPTION 'material update requires removal or frozen evidence';
    END IF;
  END IF;
  RETURN NEW;
END $$;
"""

PUBLICATION_BEFORE = "AND (b.frozen_at IS NULL"
PUBLICATION_AFTER = "AND b.state IS DISTINCT FROM 'removed' AND (b.frozen_at IS NULL"


def replace_publication_guard(before: str, after: str) -> None:
    definition = (
        op.get_bind()
        .execute(
            sa.text("SELECT pg_get_functiondef('validate_course_file_publication()'::regprocedure)")
        )
        .scalar_one()
    )
    if definition.count(before) != 1:
        raise RuntimeError("Unexpected course publication guard definition")
    op.execute(definition.replace(before, after))


def upgrade():
    op.add_column(
        "lesson_material_files",
        sa.Column("state", sa.String(16), nullable=False, server_default="active"),
    )
    op.add_column(
        "lesson_material_files",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.alter_column("lesson_material_files", "state", server_default=None)
    op.alter_column("lesson_material_files", "version", server_default=None)
    op.create_check_constraint(
        "material_file_state",
        "lesson_material_files",
        "state IN ('active','removed') AND version > 0 "
        "AND (state <> 'removed' OR frozen_at IS NULL)",
    )
    op.execute(NEW_GUARD)
    replace_publication_guard(PUBLICATION_BEFORE, PUBLICATION_AFTER)


def downgrade():
    replace_publication_guard(PUBLICATION_AFTER, PUBLICATION_BEFORE)
    op.execute(OLD_GUARD)
    op.drop_constraint("material_file_state", "lesson_material_files", type_="check")
    op.drop_column("lesson_material_files", "version")
    op.drop_column("lesson_material_files", "state")
