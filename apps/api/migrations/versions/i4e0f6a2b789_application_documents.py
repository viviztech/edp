"""Pin application document rules, bindings and submitted byte evidence."""

# ruff: noqa: E501
import sqlalchemy as sa
from alembic import op

revision = "i4e0f6a2b789"
down_revision = "h3d9e5f1a678"
branch_labels = None
depends_on = None

POLICY_GUARD_FROM = "OR policy.state <> 'published'"
POLICY_GUARD_TO = """OR NOT (policy.state = 'published' OR (
    NEW.purpose = 'application_document' AND policy.state = 'retired'
    AND policy.published_at IS NOT NULL AND EXISTS (
      SELECT 1 FROM applications a JOIN application_forms f ON f.id = a.form_id
      JOIN application_document_requirements r ON r.form_id = f.id
      WHERE a.organization_id = NEW.organization_id AND a.person_id = NEW.owner_person_id
        AND a.state = 'draft' AND r.file_policy_id = NEW.policy_id
        AND f.state IN ('published','retired') AND f.published_at >= policy.published_at
    )))"""


def replace_policy_guard(before: str, after: str) -> None:
    # Preserve every foundation lifecycle check. Fail if the expected predecessor
    # changed, rather than silently weakening a different function definition.
    definition = op.get_bind().scalar(
        sa.text("SELECT pg_get_functiondef('file_object_guard()'::regprocedure)")
    )
    if isinstance(definition, str) and definition.count(after) == 1 and before not in definition:
        return
    if not isinstance(definition, str) or definition.count(before) != 1:
        raise RuntimeError("Unexpected predecessor file lifecycle guard")
    op.execute(sa.text(definition.replace(before, after)))


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_application_document_owner_scope",
        "applications",
        ["id", "form_id", "organization_id", "person_id"],
    )
    replace_policy_guard(POLICY_GUARD_FROM, POLICY_GUARD_TO)
    op.execute("""
    CREATE FUNCTION validate_retired_application_file_pin() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF EXISTS (SELECT 1 FROM file_policies WHERE id = NEW.policy_id AND state = 'retired')
          AND NOT EXISTS (SELECT 1 FROM application_documents d JOIN applications a
            ON a.id = d.application_id JOIN application_forms f ON f.id = d.form_id
            JOIN file_policies p ON p.id = d.file_policy_id
            WHERE d.file_id = NEW.id AND d.id = NEW.resource_id
              AND d.organization_id = NEW.organization_id AND d.owner_person_id = NEW.owner_person_id
              AND d.file_policy_id = NEW.policy_id AND a.state = 'draft'
              AND f.state IN ('published','retired') AND f.published_at >= p.published_at
              AND p.published_at IS NOT NULL) THEN
        RAISE EXCEPTION 'retired policy requires typed published application pin';
      END IF;
      RETURN NEW;
    END $$;
    CREATE CONSTRAINT TRIGGER trg_retired_application_file_pin AFTER INSERT ON file_objects
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (NEW.purpose = 'application_document')
      EXECUTE FUNCTION validate_retired_application_file_pin();
    """)
    op.execute("""
CREATE TABLE application_document_requirements (
	organization_id UUID NOT NULL,
	form_id UUID NOT NULL,
	requirement_key VARCHAR(80) NOT NULL,
	label_en VARCHAR(200) NOT NULL,
	label_ta VARCHAR(200) NOT NULL,
	instructions_en VARCHAR(2000) NOT NULL,
	instructions_ta VARCHAR(2000) NOT NULL,
	file_policy_id UUID NOT NULL,
	purpose VARCHAR(32) NOT NULL,
	min_files INTEGER NOT NULL,
	max_files INTEGER NOT NULL,
	position INTEGER NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT fk_document_requirement_form_scope FOREIGN KEY(form_id, organization_id) REFERENCES application_forms (id, organization_id) ON DELETE RESTRICT,
	CONSTRAINT fk_document_requirement_policy_scope FOREIGN KEY(file_policy_id, organization_id, purpose) REFERENCES file_policies (id, organization_id, purpose) ON DELETE RESTRICT,
	UNIQUE (form_id, requirement_key),
	UNIQUE (form_id, position),
	CONSTRAINT uq_document_requirement_scope UNIQUE (id, form_id, organization_id, file_policy_id),
	CONSTRAINT document_requirement_purpose CHECK (purpose = 'application_document'),
	CONSTRAINT document_requirement_counts CHECK (min_files BETWEEN 0 AND 100 AND max_files BETWEEN 1 AND 100 AND min_files <= max_files AND position >= 0),
	CONSTRAINT document_requirement_text CHECK (requirement_key ~ '^[a-z][a-z0-9_]*$' AND length(trim(label_en)) > 0 AND length(trim(label_ta)) > 0 AND length(trim(instructions_en)) > 0 AND length(trim(instructions_ta)) > 0)
)
    """)
    op.execute("""
CREATE INDEX ix_application_document_requirements_form_id ON application_document_requirements (form_id)
    """)
    op.execute("""
CREATE INDEX ix_application_document_requirements_organization_id ON application_document_requirements (organization_id)
    """)
    op.execute("""
CREATE TABLE application_documents (
	organization_id UUID NOT NULL,
	application_id UUID NOT NULL,
	form_id UUID NOT NULL,
	requirement_id UUID NOT NULL,
	owner_person_id UUID NOT NULL,
	file_policy_id UUID NOT NULL,
	file_id UUID NOT NULL,
	purpose VARCHAR(32) NOT NULL,
	client_request_id UUID NOT NULL,
	request_digest VARCHAR(64) NOT NULL,
	removed_at TIMESTAMP WITH TIME ZONE,
	replaced_by_id UUID,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT fk_application_document_owner_scope FOREIGN KEY(application_id, form_id, organization_id, owner_person_id) REFERENCES applications (id, form_id, organization_id, person_id) ON DELETE RESTRICT,
	CONSTRAINT fk_application_document_requirement_scope FOREIGN KEY(requirement_id, form_id, organization_id, file_policy_id) REFERENCES application_document_requirements (id, form_id, organization_id, file_policy_id) ON DELETE RESTRICT,
	CONSTRAINT fk_application_document_file_scope FOREIGN KEY(file_id, organization_id, owner_person_id, purpose, id) REFERENCES file_objects (id, organization_id, owner_person_id, purpose, resource_id) ON DELETE RESTRICT,
	UNIQUE (organization_id, client_request_id),
	CONSTRAINT uq_application_document_evidence UNIQUE (id, application_id, file_id),
	CONSTRAINT uq_application_document_replacement_scope UNIQUE (id, application_id, requirement_id, organization_id, owner_person_id),
	CONSTRAINT fk_application_document_replacement_scope FOREIGN KEY(replaced_by_id, application_id, requirement_id, organization_id, owner_person_id) REFERENCES application_documents (id, application_id, requirement_id, organization_id, owner_person_id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
	CONSTRAINT application_document_purpose CHECK (purpose = 'application_document'),
	CONSTRAINT application_document_replacement CHECK (replaced_by_id IS NULL OR (removed_at IS NOT NULL AND replaced_by_id <> id)),
	CONSTRAINT application_document_digest CHECK (request_digest ~ '^[0-9a-f]{64}$'),
	UNIQUE (file_id)
)
    """)
    op.execute("""
CREATE INDEX ix_application_document_active ON application_documents (application_id, removed_at, id)
    """)
    op.execute("""
CREATE INDEX ix_application_documents_application_id ON application_documents (application_id)
    """)
    op.execute("""
CREATE INDEX ix_application_documents_organization_id ON application_documents (organization_id)
    """)
    op.execute("""
CREATE TABLE application_document_evidence (
	application_id UUID NOT NULL,
	document_id UUID NOT NULL,
	file_id UUID NOT NULL,
	file_version INTEGER NOT NULL,
	storage_version VARCHAR(1024) NOT NULL,
	byte_size INTEGER NOT NULL,
	sha256 VARCHAR(64) NOT NULL,
	frozen_at TIMESTAMP WITH TIME ZONE NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT fk_application_document_evidence_scope FOREIGN KEY(document_id, application_id, file_id) REFERENCES application_documents (id, application_id, file_id) ON DELETE RESTRICT,
	CONSTRAINT application_document_evidence_values CHECK (file_version > 0 AND byte_size > 0 AND length(storage_version) > 0 AND sha256 ~ '^[0-9a-f]{64}$'),
	UNIQUE (document_id)
)
    """)
    op.execute("""
CREATE INDEX ix_application_document_evidence_application_id ON application_document_evidence (application_id)
    """)

    op.execute("""
    CREATE FUNCTION protect_document_requirement() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE form_state varchar;
    BEGIN
      IF TG_OP <> 'INSERT' THEN
        SELECT state INTO form_state FROM application_forms WHERE id = OLD.form_id FOR UPDATE;
        IF form_state IS DISTINCT FROM 'draft' THEN
          RAISE EXCEPTION 'published document requirements are immutable';
        END IF;
      END IF;
      IF TG_OP <> 'DELETE' THEN
        SELECT state INTO form_state FROM application_forms WHERE id = NEW.form_id FOR UPDATE;
        IF form_state IS DISTINCT FROM 'draft' THEN
          RAISE EXCEPTION 'published document requirements are immutable';
        END IF;
        IF NOT EXISTS (SELECT 1 FROM file_policies WHERE id = NEW.file_policy_id
            AND organization_id = NEW.organization_id AND purpose = 'application_document'
            AND state IN ('published','retired') AND published_at IS NOT NULL
            AND max_files >= NEW.max_files) THEN
          RAISE EXCEPTION 'document requirement policy invalid';
        END IF;
        IF TG_OP = 'INSERT' AND (SELECT count(*) FROM application_document_requirements
            WHERE form_id = NEW.form_id) >= 20 THEN
          RAISE EXCEPTION 'too many document requirements';
        END IF;
      END IF;
      RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
    END $$;
    CREATE TRIGGER trg_document_requirement_immutable BEFORE INSERT OR UPDATE OR DELETE
      ON application_document_requirements FOR EACH ROW EXECUTE FUNCTION protect_document_requirement();

    CREATE FUNCTION validate_form_document_policy() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF OLD.state <> 'draft' AND EXISTS (
          SELECT 1 FROM application_document_requirements WHERE form_id = OLD.id)
          AND (NEW.published_at IS DISTINCT FROM OLD.published_at
            OR NEW.published_by_id IS DISTINCT FROM OLD.published_by_id) THEN
        RAISE EXCEPTION 'published document policy provenance is immutable';
      END IF;
      IF OLD.state = 'draft' AND NEW.state = 'published' THEN
        PERFORM p.id FROM file_policies p JOIN application_document_requirements r
          ON r.file_policy_id = p.id WHERE r.form_id = NEW.id FOR SHARE OF p;
        IF EXISTS (SELECT 1 FROM application_document_requirements r JOIN file_policies p
            ON p.id = r.file_policy_id WHERE r.form_id = NEW.id
            AND (p.state <> 'published' OR p.published_at IS NULL OR NEW.published_at IS NULL
              OR p.published_at > NEW.published_at OR r.max_files > p.max_files))
            OR EXISTS (SELECT 1 FROM application_document_requirements r JOIN file_policies p
              ON p.id = r.file_policy_id WHERE r.form_id = NEW.id
              GROUP BY p.id,p.max_files HAVING sum(r.min_files) > p.max_files)
            OR (SELECT count(*) FROM application_document_requirements WHERE form_id = NEW.id) > 20 THEN
          RAISE EXCEPTION 'document requirement publication invalid';
        END IF;
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER trg_application_form_documents BEFORE UPDATE ON application_forms
      FOR EACH ROW EXECUTE FUNCTION validate_form_document_policy();

    CREATE FUNCTION protect_application_document() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE app_state varchar; DECLARE rule_max integer; DECLARE policy_max integer;
    BEGIN
      IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'document metadata is retained'; END IF;
      SELECT state INTO app_state FROM applications WHERE id = NEW.application_id FOR UPDATE;
      IF app_state IS DISTINCT FROM 'draft' THEN
        RAISE EXCEPTION 'submitted application documents are immutable';
      END IF;
      IF TG_OP = 'UPDATE' THEN
        IF (to_jsonb(NEW) - ARRAY['removed_at','replaced_by_id']) IS DISTINCT FROM
            (to_jsonb(OLD) - ARRAY['removed_at','replaced_by_id']) OR OLD.removed_at IS NOT NULL
            OR EXISTS (SELECT 1 FROM application_document_evidence WHERE document_id = OLD.id) THEN
          RAISE EXCEPTION 'document identity and frozen evidence are immutable';
        END IF;
      ELSIF NEW.removed_at IS NOT NULL OR NEW.replaced_by_id IS NOT NULL THEN
        RAISE EXCEPTION 'new document must be active';
      END IF;
      IF NOT EXISTS (SELECT 1 FROM file_objects f JOIN application_forms a ON a.id = NEW.form_id
          JOIN file_policies p ON p.id = NEW.file_policy_id
          WHERE f.id = NEW.file_id AND f.policy_id = p.id AND a.state IN ('published','retired')
            AND a.published_at IS NOT NULL AND p.published_at IS NOT NULL
            AND p.published_at <= a.published_at AND p.state IN ('published','retired')) THEN
        RAISE EXCEPTION 'document policy pin invalid';
      END IF;
      IF NEW.removed_at IS NULL THEN
        SELECT max_files INTO rule_max FROM application_document_requirements
          WHERE id = NEW.requirement_id;
        SELECT max_files INTO policy_max FROM file_policies WHERE id = NEW.file_policy_id;
        IF (SELECT count(*) FROM application_documents WHERE application_id = NEW.application_id
              AND requirement_id = NEW.requirement_id AND removed_at IS NULL AND id <> NEW.id) >= rule_max
            OR (SELECT count(*) FROM application_documents WHERE application_id = NEW.application_id
              AND file_policy_id = NEW.file_policy_id AND removed_at IS NULL AND id <> NEW.id) >= policy_max THEN
          RAISE EXCEPTION 'document count exceeded';
        END IF;
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER trg_application_document_immutable BEFORE INSERT OR UPDATE OR DELETE
      ON application_documents FOR EACH ROW EXECUTE FUNCTION protect_application_document();

    CREATE FUNCTION protect_application_document_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE app_state varchar;
    BEGIN
      IF TG_OP <> 'INSERT' THEN RAISE EXCEPTION 'submitted document evidence is immutable'; END IF;
      SELECT state INTO app_state FROM applications WHERE id = NEW.application_id FOR UPDATE;
      IF app_state IS DISTINCT FROM 'draft' THEN RAISE EXCEPTION 'document evidence requires draft'; END IF;
      PERFORM f.id FROM file_objects f JOIN application_documents d ON d.file_id = f.id
        WHERE d.id = NEW.document_id FOR UPDATE OF f;
      IF NOT EXISTS (SELECT 1 FROM application_documents d JOIN file_objects f ON f.id = d.file_id
          WHERE d.id = NEW.document_id AND d.application_id = NEW.application_id
            AND d.removed_at IS NULL AND f.id = NEW.file_id AND f.state = 'clean'
            AND f.evidence_frozen AND f.retention_until > CURRENT_TIMESTAMP
            AND f.version = NEW.file_version AND f.storage_version = NEW.storage_version
            AND f.stored_sha256 = NEW.sha256 AND f.stored_byte_size = NEW.byte_size) THEN
        RAISE EXCEPTION 'document evidence must pin exact clean bytes';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER trg_application_document_evidence_immutable BEFORE INSERT OR UPDATE OR DELETE
      ON application_document_evidence FOR EACH ROW EXECUTE FUNCTION protect_application_document_evidence();

    CREATE FUNCTION validate_application_document_submission() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF OLD.state = 'draft' AND NEW.state <> 'draft' THEN
        PERFORM d.id FROM application_documents d WHERE d.application_id = NEW.id ORDER BY d.id FOR UPDATE;
        PERFORM f.id FROM file_objects f JOIN application_documents d ON d.file_id = f.id
          WHERE d.application_id = NEW.id AND d.removed_at IS NULL ORDER BY f.id FOR UPDATE OF f;
        IF EXISTS (SELECT 1 FROM application_document_requirements r LEFT JOIN application_documents d
              ON d.requirement_id = r.id AND d.application_id = NEW.id AND d.removed_at IS NULL
              WHERE r.form_id = NEW.form_id GROUP BY r.id,r.min_files,r.max_files
              HAVING count(d.id) < r.min_files OR count(d.id) > r.max_files)
            OR EXISTS (SELECT 1 FROM application_documents d JOIN file_objects f ON f.id = d.file_id
              LEFT JOIN application_document_evidence e ON e.document_id = d.id
              WHERE d.application_id = NEW.id AND d.removed_at IS NULL
                AND (f.state <> 'clean' OR NOT f.evidence_frozen OR f.retention_until <= CURRENT_TIMESTAMP
                  OR e.id IS NULL OR e.storage_version IS DISTINCT FROM f.storage_version
                  OR e.sha256 IS DISTINCT FROM f.stored_sha256 OR e.byte_size IS DISTINCT FROM f.stored_byte_size)) THEN
          RAISE EXCEPTION 'application requires exact clean document evidence';
        END IF;
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER trg_application_document_submission BEFORE UPDATE ON applications
      FOR EACH ROW EXECUTE FUNCTION validate_application_document_submission();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_retired_application_file_pin ON file_objects")
    op.execute("DROP FUNCTION IF EXISTS validate_retired_application_file_pin()")
    replace_policy_guard(POLICY_GUARD_TO, POLICY_GUARD_FROM)
    op.execute("DROP TRIGGER trg_application_document_submission ON applications")
    op.execute("DROP FUNCTION validate_application_document_submission()")
    op.execute("DROP TRIGGER trg_application_form_documents ON application_forms")
    op.execute("DROP FUNCTION validate_form_document_policy()")
    op.execute(
        "DROP TRIGGER trg_application_document_evidence_immutable ON application_document_evidence"
    )
    op.execute("DROP FUNCTION protect_application_document_evidence()")
    op.execute("DROP TRIGGER trg_application_document_immutable ON application_documents")
    op.execute("DROP FUNCTION protect_application_document()")
    op.execute(
        "DROP TRIGGER trg_document_requirement_immutable ON application_document_requirements"
    )
    op.execute("DROP FUNCTION protect_document_requirement()")
    op.drop_table("application_document_evidence")
    op.drop_table("application_documents")
    op.drop_table("application_document_requirements")
    op.drop_constraint("uq_application_document_owner_scope", "applications", type_="unique")
