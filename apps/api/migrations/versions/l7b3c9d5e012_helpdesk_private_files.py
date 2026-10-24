"""Freeze shared helpdesk files on immutable message selection."""

# ruff: noqa: E501
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "l7b3c9d5e012"
down_revision = "k6a2b8c4d901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "helpdesk_messages",
        sa.Column(
            "shared_file_ids",
            postgresql.ARRAY(sa.Uuid()),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
        ),
    )
    op.create_unique_constraint(
        "uq_helpdesk_message_file_scope",
        "helpdesk_messages",
        ["id", "ticket_id", "organization_id", "author_user_id", "internal"],
    )
    op.create_check_constraint(
        "helpdesk_message_file_count", "helpdesk_messages", "cardinality(shared_file_ids) <= 100"
    )
    op.execute("""
CREATE TABLE helpdesk_files (
	organization_id UUID NOT NULL,
	ticket_id UUID NOT NULL,
	author_user_id UUID NOT NULL,
	owner_person_id UUID NOT NULL,
	policy_id UUID NOT NULL,
	file_id UUID NOT NULL,
	purpose VARCHAR(32) NOT NULL,
	client_request_id UUID NOT NULL,
	request_digest VARCHAR(64) NOT NULL,
	internal BOOLEAN NOT NULL,
	state VARCHAR(16) NOT NULL,
	version INTEGER NOT NULL,
	message_id UUID,
	frozen_file_version INTEGER,
	frozen_storage_version VARCHAR(1024),
	frozen_sha256 VARCHAR(64),
	frozen_byte_size INTEGER,
	frozen_at TIMESTAMP WITH TIME ZONE,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT fk_helpdesk_file_ticket FOREIGN KEY(ticket_id, organization_id) REFERENCES helpdesk_tickets (id, organization_id) ON DELETE RESTRICT,
	CONSTRAINT fk_helpdesk_file_message_scope FOREIGN KEY(message_id, ticket_id, organization_id, author_user_id, internal) REFERENCES helpdesk_messages (id, ticket_id, organization_id, author_user_id, internal) ON DELETE RESTRICT,
	CONSTRAINT fk_helpdesk_file_object_scope FOREIGN KEY(file_id, organization_id, owner_person_id, purpose, id) REFERENCES file_objects (id, organization_id, owner_person_id, purpose, resource_id) ON DELETE RESTRICT,
	CONSTRAINT fk_helpdesk_file_policy_scope FOREIGN KEY(policy_id, organization_id, purpose) REFERENCES file_policies (id, organization_id, purpose) ON DELETE RESTRICT,
	UNIQUE (organization_id, client_request_id),
	CONSTRAINT helpdesk_file_purpose CHECK (purpose = 'helpdesk_attachment'),
	CONSTRAINT helpdesk_file_state CHECK (state IN ('staged','removed','posted') AND version > 0),
	CONSTRAINT helpdesk_file_digest CHECK (request_digest ~ '^[0-9a-f]{64}$'),
	CONSTRAINT helpdesk_file_frozen_evidence CHECK ((state = 'posted' AND message_id IS NOT NULL AND frozen_file_version > 0 AND frozen_file_version IS NOT NULL AND frozen_storage_version IS NOT NULL AND frozen_sha256 IS NOT NULL AND frozen_byte_size > 0 AND frozen_byte_size IS NOT NULL AND frozen_at IS NOT NULL) OR (state <> 'posted' AND message_id IS NULL AND frozen_file_version IS NULL AND frozen_storage_version IS NULL AND frozen_sha256 IS NULL AND frozen_byte_size IS NULL AND frozen_at IS NULL)),
	FOREIGN KEY(author_user_id) REFERENCES users (id) ON DELETE RESTRICT,
	UNIQUE (file_id)
)
    """)
    op.execute("""
CREATE INDEX ix_helpdesk_file_message ON helpdesk_files (organization_id, message_id, id)
    """)
    op.execute("""
CREATE INDEX ix_helpdesk_file_ticket ON helpdesk_files (organization_id, ticket_id, id)
    """)

    op.execute("""
    CREATE FUNCTION helpdesk_file_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE ticket_state varchar; DECLARE rule_limit integer;
    BEGIN
      IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'helpdesk file metadata is retained'; END IF;
      SELECT status INTO ticket_state FROM helpdesk_tickets
        WHERE id = NEW.ticket_id AND organization_id = NEW.organization_id FOR UPDATE;
      IF ticket_state IS NULL OR ticket_state IN ('resolved','closed') THEN
        RAISE EXCEPTION 'helpdesk attachment requires writable ticket';
      END IF;
      IF NOT EXISTS (SELECT 1 FROM users u JOIN file_objects f ON f.id = NEW.file_id
          JOIN file_policies p ON p.id = NEW.policy_id
          WHERE u.id = NEW.author_user_id AND u.person_id = NEW.owner_person_id
            AND f.policy_id = p.id AND p.published_at IS NOT NULL
            AND p.state IN ('published','retired') AND f.created_at >= p.published_at) THEN
        RAISE EXCEPTION 'helpdesk file owner and approved policy must match';
      END IF;
      IF TG_OP = 'INSERT' THEN
        IF NEW.state <> 'staged' OR NEW.version <> 1 OR NEW.message_id IS NOT NULL
            OR NOT EXISTS (SELECT 1 FROM file_policies WHERE id = NEW.policy_id
              AND state = 'published') THEN
          RAISE EXCEPTION 'helpdesk file must begin staged under published policy';
        END IF;
        SELECT max_files INTO rule_limit FROM file_policies WHERE id = NEW.policy_id;
        IF (SELECT count(*) FROM helpdesk_files WHERE ticket_id = NEW.ticket_id
            AND author_user_id = NEW.author_user_id AND state = 'staged') >= rule_limit THEN
          RAISE EXCEPTION 'helpdesk staging limit exceeded';
        END IF;
      ELSE
        IF OLD.state <> 'staged' OR NEW.state NOT IN ('removed','posted')
            OR NEW.version <> OLD.version + 1 OR
            (to_jsonb(NEW) - ARRAY['state','version','message_id','frozen_file_version',
              'frozen_storage_version','frozen_sha256','frozen_byte_size','frozen_at']) IS DISTINCT FROM
            (to_jsonb(OLD) - ARRAY['state','version','message_id','frozen_file_version',
              'frozen_storage_version','frozen_sha256','frozen_byte_size','frozen_at']) THEN
          RAISE EXCEPTION 'helpdesk file identity and posted evidence are immutable';
        END IF;
        IF NEW.state = 'posted' AND NOT EXISTS (
            SELECT 1 FROM helpdesk_messages m JOIN file_objects f ON f.id = NEW.file_id
            WHERE m.id = NEW.message_id AND m.ticket_id = NEW.ticket_id
              AND m.organization_id = NEW.organization_id AND m.author_user_id = NEW.author_user_id
              AND m.internal = NEW.internal AND NEW.id = ANY(m.shared_file_ids)
              AND f.state = 'clean' AND f.evidence_frozen AND f.retention_until > CURRENT_TIMESTAMP
              AND NEW.frozen_file_version = f.version AND NEW.frozen_storage_version = f.storage_version
              AND NEW.frozen_sha256 = f.stored_sha256 AND NEW.frozen_byte_size = f.stored_byte_size
              AND NEW.frozen_at IS NOT NULL) THEN
          RAISE EXCEPTION 'posted helpdesk file must pin selected exact clean bytes';
        END IF;
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER trg_helpdesk_file_immutable BEFORE INSERT OR UPDATE OR DELETE ON helpdesk_files
      FOR EACH ROW EXECUTE FUNCTION helpdesk_file_guard();

    CREATE FUNCTION helpdesk_message_file_selection() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE selected_count integer; DECLARE policy_count integer;
    BEGIN
      IF cardinality(NEW.shared_file_ids) = 0 THEN RETURN NEW; END IF;
      IF cardinality(NEW.shared_file_ids) <> (SELECT count(DISTINCT id)
          FROM unnest(NEW.shared_file_ids) id) OR cardinality(NEW.shared_file_ids) > 100 THEN
        RAISE EXCEPTION 'duplicate or excess message file selection';
      END IF;
      PERFORM id FROM helpdesk_tickets WHERE id = NEW.ticket_id
        AND organization_id = NEW.organization_id AND version = NEW.ticket_version
        AND status NOT IN ('resolved','closed') FOR UPDATE;
      IF NOT FOUND THEN RAISE EXCEPTION 'message requires current writable ticket version'; END IF;
      PERFORM id FROM helpdesk_files WHERE id = ANY(NEW.shared_file_ids) ORDER BY id FOR UPDATE;
      SELECT count(*),count(DISTINCT b.policy_id) INTO selected_count,policy_count
        FROM helpdesk_files b JOIN file_objects f ON f.id = b.file_id
        WHERE b.id = ANY(NEW.shared_file_ids) AND b.organization_id = NEW.organization_id
          AND b.ticket_id = NEW.ticket_id AND b.author_user_id = NEW.author_user_id
          AND b.internal = NEW.internal AND b.state = 'staged' AND f.state = 'clean'
          AND f.retention_until > CURRENT_TIMESTAMP;
      IF selected_count <> cardinality(NEW.shared_file_ids) OR policy_count <> 1
          OR EXISTS (SELECT 1 FROM helpdesk_files b JOIN file_policies p ON p.id = b.policy_id
            WHERE b.id = ANY(NEW.shared_file_ids)
            GROUP BY p.id,p.max_files HAVING count(*) > p.max_files) THEN
        RAISE EXCEPTION 'message files require scoped clean staged evidence under one policy';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER trg_helpdesk_message_file_selection BEFORE INSERT ON helpdesk_messages
      FOR EACH ROW EXECUTE FUNCTION helpdesk_message_file_selection();

    CREATE FUNCTION helpdesk_message_files_required() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF EXISTS (SELECT 1 FROM unnest(NEW.shared_file_ids) selected_id WHERE NOT EXISTS (
          SELECT 1 FROM helpdesk_files b JOIN file_objects f ON f.id = b.file_id
          WHERE b.id = selected_id AND b.message_id = NEW.id AND b.ticket_id = NEW.ticket_id
            AND b.organization_id = NEW.organization_id AND b.author_user_id = NEW.author_user_id
            AND b.internal = NEW.internal AND b.state = 'posted'
            AND f.state = 'clean' AND f.evidence_frozen AND f.retention_until > CURRENT_TIMESTAMP
            AND b.frozen_storage_version = f.storage_version AND b.frozen_sha256 = f.stored_sha256
            AND b.frozen_byte_size = f.stored_byte_size AND b.frozen_at IS NOT NULL)) THEN
        RAISE EXCEPTION 'message selected files require immutable exact frozen evidence';
      END IF;
      RETURN NEW;
    END $$;
    CREATE CONSTRAINT TRIGGER trg_helpdesk_message_files_required AFTER INSERT ON helpdesk_messages
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION helpdesk_message_files_required();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_helpdesk_message_files_required ON helpdesk_messages")
    op.execute("DROP FUNCTION helpdesk_message_files_required()")
    op.execute("DROP TRIGGER trg_helpdesk_message_file_selection ON helpdesk_messages")
    op.execute("DROP FUNCTION helpdesk_message_file_selection()")
    op.execute("DROP TRIGGER trg_helpdesk_file_immutable ON helpdesk_files")
    op.execute("DROP FUNCTION helpdesk_file_guard()")
    op.drop_table("helpdesk_files")
    op.drop_constraint("helpdesk_message_file_count", "helpdesk_messages", type_="check")
    op.drop_constraint("uq_helpdesk_message_file_scope", "helpdesk_messages", type_="unique")
    op.drop_column("helpdesk_messages", "shared_file_ids")
