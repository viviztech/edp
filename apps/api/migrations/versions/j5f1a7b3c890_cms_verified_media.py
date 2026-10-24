"""CMS typed private bytes and versioned public evidence; legacy metadata stays unbacked."""

import sqlalchemy as sa
from alembic import op

revision = "j5f1a7b3c890"
down_revision = "i4e0f6a2b789"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "cms_assets", sa.Column("version", sa.Integer(), server_default="1", nullable=False)
    )
    op.add_column("cms_assets", sa.Column("client_request_id", sa.Uuid(), nullable=True))
    op.add_column("cms_assets", sa.Column("request_digest", sa.String(64), nullable=True))
    op.add_column("cms_assets", sa.Column("public_file_id", sa.Uuid(), nullable=True))
    op.add_column("cms_assets", sa.Column("public_storage_version", sa.String(1024), nullable=True))
    op.add_column("cms_assets", sa.Column("public_sha256", sa.String(64), nullable=True))
    op.add_column("cms_assets", sa.Column("public_byte_size", sa.Integer(), nullable=True))
    op.alter_column("cms_assets", "version", server_default=None)
    op.create_unique_constraint(
        "uq_cms_assets_id_organization_id", "cms_assets", ["id", "organization_id"]
    )
    op.create_unique_constraint(
        "uq_cms_assets_organization_id_client_request_id",
        "cms_assets",
        ["organization_id", "client_request_id"],
    )
    op.create_check_constraint("cms_asset_version", "cms_assets", "version > 0")
    op.create_check_constraint(
        "cms_asset_public_evidence",
        "cms_assets",
        "(public_file_id IS NULL AND public_storage_version IS NULL "
        "AND public_sha256 IS NULL AND public_byte_size IS NULL) OR "
        "(public_file_id IS NOT NULL AND public_storage_version IS NOT NULL "
        "AND length(public_storage_version) > 0 AND public_sha256 IS NOT NULL "
        "AND public_byte_size IS NOT NULL "
        "AND public_sha256 ~ '^[0-9a-f]{64}$' AND public_byte_size > 0)",
    )
    op.create_table(
        "cms_asset_files",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("owner_person_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("file_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(24), nullable=False),
        sa.UniqueConstraint("asset_id", "role"),
        sa.UniqueConstraint("file_id", "asset_id", "organization_id"),
        sa.ForeignKeyConstraint(
            ["asset_id", "organization_id"],
            ["cms_assets.id", "cms_assets.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["file_id", "organization_id", "owner_person_id", "purpose", "asset_id"],
            [
                "file_objects.id",
                "file_objects.organization_id",
                "file_objects.owner_person_id",
                "file_objects.purpose",
                "file_objects.resource_id",
            ],
            name="fk_cms_asset_file_context",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("purpose = 'cms_asset'", name="cms_asset_file_purpose"),
        sa.CheckConstraint("role IN ('source','public_derivative')", name="cms_asset_file_role"),
    )
    op.create_foreign_key(
        "fk_cms_public_asset_binding",
        "cms_assets",
        "cms_asset_files",
        ["public_file_id", "id", "organization_id"],
        ["file_id", "asset_id", "organization_id"],
        ondelete="RESTRICT",
    )
    op.execute("""
      CREATE FUNCTION cms_asset_file_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN RAISE EXCEPTION 'CMS file bindings are immutable'; END $$;
      CREATE TRIGGER cms_asset_file_immutable BEFORE UPDATE OR DELETE ON cms_asset_files
      FOR EACH ROW EXECUTE FUNCTION cms_asset_file_immutable();
      CREATE FUNCTION cms_asset_file_insert_guard() RETURNS trigger LANGUAGE plpgsql AS $$
      DECLARE a cms_assets%ROWTYPE; f file_objects%ROWTYPE; s file_objects%ROWTYPE;
      BEGIN
        SELECT * INTO a FROM cms_assets WHERE id=NEW.asset_id
          AND organization_id=NEW.organization_id;
        SELECT * INTO f FROM file_objects WHERE id=NEW.file_id;
        IF a.id IS NULL OR f.id IS NULL OR f.expected_media_type <> a.media_type THEN
          RAISE EXCEPTION 'CMS file metadata mismatch';
        END IF;
        IF NEW.role='source' AND f.expected_byte_size <> a.byte_size THEN
          RAISE EXCEPTION 'CMS source size mismatch';
        END IF;
        IF NEW.role='public_derivative' THEN
          SELECT o.* INTO s FROM file_objects o JOIN cms_asset_files b ON b.file_id=o.id
            WHERE b.asset_id=NEW.asset_id AND b.role='source';
          IF a.media_type='application/pdf' OR s.id IS NULL
             OR f.owner_person_id<>s.owner_person_id OR f.policy_id<>s.policy_id THEN
            RAISE EXCEPTION 'CMS derivative context mismatch';
          END IF;
        END IF;
        RETURN NEW;
      END $$;
      CREATE TRIGGER cms_asset_file_insert_guard BEFORE INSERT ON cms_asset_files
      FOR EACH ROW EXECUTE FUNCTION cms_asset_file_insert_guard();
      CREATE FUNCTION cms_asset_public_guard() RETURNS trigger LANGUAGE plpgsql AS $$
      DECLARE f file_objects%ROWTYPE; binding_role varchar;
      BEGIN
        IF ROW(NEW.id,NEW.organization_id,NEW.storage_key,NEW.filename,NEW.media_type,NEW.byte_size,
               NEW.title,NEW.client_request_id,NEW.request_digest)
          IS DISTINCT FROM ROW(OLD.id,OLD.organization_id,OLD.storage_key,OLD.filename,
               OLD.media_type,OLD.byte_size,OLD.title,OLD.client_request_id,OLD.request_digest) THEN
          RAISE EXCEPTION 'CMS source identity is immutable';
        END IF;
        IF ROW(NEW.visibility,NEW.public_file_id,NEW.public_storage_version,
               NEW.public_sha256,NEW.public_byte_size)
          IS DISTINCT FROM ROW(OLD.visibility,OLD.public_file_id,OLD.public_storage_version,
               OLD.public_sha256,OLD.public_byte_size)
          AND NEW.version <> OLD.version + 1 THEN
          RAISE EXCEPTION 'CMS publication requires version change';
        END IF;
        IF NEW.public_file_id IS NOT NULL AND NEW.visibility='public' THEN
          SELECT o.* INTO f
            FROM file_objects o JOIN cms_asset_files b ON b.file_id=o.id
            WHERE b.asset_id=NEW.id AND b.organization_id=NEW.organization_id
              AND b.file_id=NEW.public_file_id;
          SELECT role INTO binding_role FROM cms_asset_files
            WHERE asset_id=NEW.id AND file_id=NEW.public_file_id;
          IF f.id IS NULL OR f.state<>'clean' OR NOT f.evidence_frozen
             OR f.retention_until<=CURRENT_TIMESTAMP OR f.deleted_at IS NOT NULL
             OR NEW.public_storage_version IS DISTINCT FROM f.storage_version
             OR NEW.public_sha256 IS DISTINCT FROM f.stored_sha256
             OR NEW.public_byte_size IS DISTINCT FROM f.stored_byte_size
             OR (NEW.media_type='application/pdf' AND binding_role<>'source')
             OR (NEW.media_type<>'application/pdf' AND binding_role<>'public_derivative') THEN
            RAISE EXCEPTION 'CMS publication requires exact clean bound evidence';
          END IF;
        END IF;
        RETURN NEW;
      END $$;
      CREATE TRIGGER cms_asset_public_guard BEFORE UPDATE ON cms_assets
      FOR EACH ROW EXECUTE FUNCTION cms_asset_public_guard();
    """)


def downgrade():
    op.execute(
        "DROP TRIGGER cms_asset_public_guard ON cms_assets; "
        "DROP FUNCTION cms_asset_public_guard(); "
        "DROP TRIGGER cms_asset_file_insert_guard ON cms_asset_files; "
        "DROP FUNCTION cms_asset_file_insert_guard(); "
        "DROP TRIGGER cms_asset_file_immutable ON cms_asset_files; "
        "DROP FUNCTION cms_asset_file_immutable();"
    )
    op.drop_constraint("fk_cms_public_asset_binding", "cms_assets", type_="foreignkey")
    op.drop_table("cms_asset_files")
    op.drop_constraint("cms_asset_public_evidence", "cms_assets", type_="check")
    op.drop_constraint("cms_asset_version", "cms_assets", type_="check")
    op.drop_constraint(
        "uq_cms_assets_organization_id_client_request_id", "cms_assets", type_="unique"
    )
    op.drop_constraint("uq_cms_assets_id_organization_id", "cms_assets", type_="unique")
    for name in (
        "public_byte_size",
        "public_sha256",
        "public_storage_version",
        "public_file_id",
        "request_digest",
        "client_request_id",
        "version",
    ):
        op.drop_column("cms_assets", name)
