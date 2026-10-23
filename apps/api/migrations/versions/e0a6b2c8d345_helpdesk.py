"""helpdesk"""

import sqlalchemy as sa
from alembic import op

revision = "e0a6b2c8d345"
down_revision = "d9f5a1b7c234"
branch_labels = None
depends_on = None


def install_guards() -> None:
    op.execute("""
        CREATE FUNCTION helpdesk_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'helpdesk evidence is append-only'; END $$;
        CREATE TRIGGER helpdesk_message_immutable BEFORE UPDATE OR DELETE ON helpdesk_messages
          FOR EACH ROW EXECUTE FUNCTION helpdesk_immutable();
        CREATE TRIGGER helpdesk_attachment_immutable BEFORE UPDATE OR DELETE ON helpdesk_attachments
          FOR EACH ROW EXECUTE FUNCTION helpdesk_immutable();
        CREATE TRIGGER helpdesk_history_immutable BEFORE UPDATE OR DELETE ON helpdesk_history
          FOR EACH ROW EXECUTE FUNCTION helpdesk_immutable();
        CREATE TRIGGER helpdesk_assignment_immutable BEFORE UPDATE OR DELETE ON helpdesk_assignments
          FOR EACH ROW EXECUTE FUNCTION helpdesk_immutable();

        CREATE FUNCTION helpdesk_ticket_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'helpdesk tickets cannot be deleted'; END IF;
          IF TG_OP = 'INSERT' THEN
            IF NEW.status <> 'open' OR NEW.version <> 1 OR NEW.assignee_user_id IS NOT NULL THEN
              RAISE EXCEPTION 'helpdesk tickets must begin open';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM participants p JOIN users u ON u.person_id = p.person_id
                WHERE p.id = NEW.owner_participant_id AND p.organization_id = NEW.organization_id
                  AND u.id = NEW.owner_user_id) THEN
              RAISE EXCEPTION 'helpdesk owner must match participant';
            END IF;
          ELSE
            IF ROW(NEW.id, NEW.organization_id, NEW.owner_participant_id, NEW.owner_user_id,
                   NEW.request_id, NEW.request_digest, NEW.number,
                   NEW.category, NEW.subject, NEW.created_at)
               IS DISTINCT FROM ROW(OLD.id, OLD.organization_id,
                   OLD.owner_participant_id, OLD.owner_user_id, OLD.request_id,
                   OLD.request_digest, OLD.number, OLD.category, OLD.subject, OLD.created_at) THEN
              RAISE EXCEPTION 'helpdesk identity is immutable';
            END IF;
            IF NEW.version <> OLD.version + 1 THEN
              RAISE EXCEPTION 'invalid helpdesk version'; END IF;
            IF NEW.status <> OLD.status AND NOT (
                (OLD.status = 'open' AND NEW.status = 'assigned') OR
                (OLD.status = 'assigned' AND NEW.status = 'in_progress') OR
                (OLD.status = 'in_progress' AND NEW.status IN ('waiting_for_user','resolved')) OR
                (OLD.status = 'waiting_for_user' AND NEW.status IN ('in_progress','resolved')) OR
                (OLD.status = 'resolved' AND NEW.status = 'closed') OR
                (OLD.status IN ('resolved','closed') AND NEW.status = 'open'
                  AND NEW.assignee_user_id IS NULL)) THEN
              RAISE EXCEPTION 'invalid helpdesk lifecycle';
            END IF;
            IF OLD.status IN ('resolved','closed') AND NEW.status = OLD.status THEN
              RAISE EXCEPTION 'resolved helpdesk tickets require explicit close or reopen';
            END IF;
          END IF;
          IF NEW.assignee_user_id IS NOT NULL AND
             (TG_OP = 'INSERT' OR NEW.assignee_user_id IS DISTINCT FROM OLD.assignee_user_id)
             AND NOT EXISTS (
              SELECT 1 FROM users u WHERE u.id = NEW.assignee_user_id AND u.status = 'active'
                AND EXISTS (SELECT 1 FROM user_roles ur
                  JOIN role_permissions rp ON rp.role_id = ur.role_id
                  WHERE ur.user_id = u.id AND ur.organization_id = NEW.organization_id
                    AND rp.permission_code = 'ticket.view')
                AND EXISTS (SELECT 1 FROM user_roles ur
                  JOIN role_permissions rp ON rp.role_id = ur.role_id
                  WHERE ur.user_id = u.id AND ur.organization_id = NEW.organization_id
                    AND rp.permission_code = 'ticket.update')) THEN
            RAISE EXCEPTION 'helpdesk assignee must be eligible in organization';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER helpdesk_ticket_evidence
          BEFORE INSERT OR UPDATE OR DELETE ON helpdesk_tickets
          FOR EACH ROW EXECUTE FUNCTION helpdesk_ticket_guard();

        CREATE FUNCTION helpdesk_ticket_history_required() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM helpdesk_history h WHERE h.ticket_id = NEW.id
              AND h.organization_id = NEW.organization_id AND h.version = NEW.version
              AND h.status = NEW.status AND h.priority = NEW.priority) THEN
            RAISE EXCEPTION 'helpdesk version requires matching immutable history';
          END IF;
          RETURN NEW;
        END $$;
        CREATE CONSTRAINT TRIGGER helpdesk_history_required
          AFTER INSERT OR UPDATE ON helpdesk_tickets DEFERRABLE INITIALLY DEFERRED
          FOR EACH ROW EXECUTE FUNCTION helpdesk_ticket_history_required();

        CREATE FUNCTION helpdesk_notice_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'helpdesk notice identity cannot be deleted'; END IF;
          IF ROW(NEW.id, NEW.organization_id, NEW.ticket_id, NEW.recipient_user_id, NEW.event,
                 NEW.ticket_version, NEW.created_at) IS DISTINCT FROM
             ROW(OLD.id, OLD.organization_id, OLD.ticket_id, OLD.recipient_user_id, OLD.event,
                 OLD.ticket_version, OLD.created_at)
                 OR OLD.read_at IS NOT NULL OR NEW.read_at IS NULL
                 OR NEW.version <> OLD.version + 1 THEN
            RAISE EXCEPTION 'only unread helpdesk notices may be marked read';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER helpdesk_notice_evidence BEFORE UPDATE OR DELETE ON helpdesk_notices
          FOR EACH ROW EXECUTE FUNCTION helpdesk_notice_guard();

        CREATE FUNCTION helpdesk_preference_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'helpdesk preference cannot be deleted'; END IF;
          IF ROW(NEW.id, NEW.organization_id, NEW.user_id, NEW.created_at) IS DISTINCT FROM
             ROW(OLD.id, OLD.organization_id, OLD.user_id, OLD.created_at)
             OR NEW.version <> OLD.version + 1 OR NEW.enabled = OLD.enabled THEN
            RAISE EXCEPTION 'invalid helpdesk preference update';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER helpdesk_preference_evidence BEFORE UPDATE OR DELETE ON helpdesk_preferences
          FOR EACH ROW EXECUTE FUNCTION helpdesk_preference_guard();

        CREATE FUNCTION helpdesk_attachment_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF NEW.filename !~ '^[A-Za-z0-9][A-Za-z0-9 _-]{0,115}\\.txt$'
             OR NEW.content ~* '<[[:space:]]*[!/?a-z]|javascript[[:space:]]*:'
             OR EXISTS (SELECT 1 FROM regexp_split_to_table(NEW.content, '') c
                        WHERE (ascii(c) < 32 AND c NOT IN (E'\\n',E'\\r',E'\\t'))
                           OR ascii(c) BETWEEN 127 AND 159)
             OR (SELECT count(*) FROM helpdesk_attachments a
                 WHERE a.message_id = NEW.message_id) >= 3 THEN
            RAISE EXCEPTION 'helpdesk attachments must be bounded plain text';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER helpdesk_attachment_validation BEFORE INSERT ON helpdesk_attachments
          FOR EACH ROW EXECUTE FUNCTION helpdesk_attachment_guard();
    """)
    op.execute("""
        INSERT INTO permissions(code)
          VALUES ('ticket.view'), ('ticket.assign'), ('ticket.update'), ('ticket.admin')
          ON CONFLICT DO NOTHING;
        INSERT INTO role_permissions(role_id, permission_code)
          SELECT id, p.code FROM roles CROSS JOIN permissions p WHERE name IN
          ('Super Admin','Program Director','Program Manager','Support Executive')
          AND p.code IN ('ticket.view','ticket.assign','ticket.update') ON CONFLICT DO NOTHING;
        INSERT INTO role_permissions(role_id, permission_code)
          SELECT id, 'ticket.admin' FROM roles WHERE name IN
          ('Super Admin','Program Director','Program Manager') ON CONFLICT DO NOTHING;
    """)


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "helpdesk_preferences",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version > 0", name="helpdesk_preference_version"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "user_id"),
    )
    op.create_table(
        "helpdesk_tickets",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("owner_participant_id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.Column("number", sa.String(length=40), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("priority", sa.String(length=12), nullable=False),
        sa.Column("assignee_user_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "category IN ('funding','registration','tax_compliance','marketing',"
            "'technology','business_planning','banking','mentoring','general')",
            name="helpdesk_ticket_category",
        ),
        sa.CheckConstraint(
            "priority IN ('low','normal','high','urgent')", name="helpdesk_ticket_priority"
        ),
        sa.CheckConstraint(
            "status <> 'open' OR assignee_user_id IS NULL", name="helpdesk_open_unassigned"
        ),
        sa.CheckConstraint(
            "status IN ('open','assigned','in_progress','waiting_for_user','resolved','closed')",
            name="helpdesk_ticket_status",
        ),
        sa.CheckConstraint(
            "status NOT IN ('assigned','in_progress','waiting_for_user','resolved') "
            "OR assignee_user_id IS NOT NULL",
            name="helpdesk_assigned_required",
        ),
        sa.CheckConstraint("version > 0", name="helpdesk_ticket_version"),
        sa.ForeignKeyConstraint(["assignee_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["owner_participant_id", "organization_id"],
            ["participants.id", "participants.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id"),
        sa.UniqueConstraint("number"),
        sa.UniqueConstraint("organization_id", "owner_user_id", "request_id"),
    )
    op.create_index(
        "ix_helpdesk_owner",
        "helpdesk_tickets",
        ["organization_id", "owner_user_id", "id"],
        unique=False,
    )
    op.create_index(
        "ix_helpdesk_queue",
        "helpdesk_tickets",
        ["organization_id", "assignee_user_id", "status", "id"],
        unique=False,
    )
    op.create_table(
        "helpdesk_assignments",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("from_user_id", sa.Uuid(), nullable=True),
        sa.Column("to_user_id", sa.Uuid(), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version > 0", name="helpdesk_assignment_version"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["from_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["ticket_id", "organization_id"],
            ["helpdesk_tickets.id", "helpdesk_tickets.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["to_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_id", "version"),
    )
    op.create_table(
        "helpdesk_history",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("event", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("priority", sa.String(length=12), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("staff_only", sa.Boolean(), nullable=False),
        sa.Column("private_reason", sa.Boolean(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version > 0", name="helpdesk_history_version"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["ticket_id", "organization_id"],
            ["helpdesk_tickets.id", "helpdesk_tickets.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_id", "version"),
    )
    op.create_index(
        "ix_helpdesk_history",
        "helpdesk_history",
        ["organization_id", "ticket_id", "version"],
        unique=False,
    )
    op.create_table(
        "helpdesk_messages",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("ticket_version", sa.Integer(), nullable=False),
        sa.Column("author_user_id", sa.Uuid(), nullable=False),
        sa.Column("internal", sa.Boolean(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(body) BETWEEN 1 AND 8000", name="helpdesk_message_body"),
        sa.CheckConstraint("ticket_version > 0", name="helpdesk_message_version"),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["ticket_id", "organization_id"],
            ["helpdesk_tickets.id", "helpdesk_tickets.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "ticket_id", "organization_id"),
        sa.UniqueConstraint("ticket_id", "ticket_version"),
    )
    op.create_index(
        "ix_helpdesk_messages",
        "helpdesk_messages",
        ["organization_id", "ticket_id", "ticket_version"],
        unique=False,
    )
    op.create_table(
        "helpdesk_notices",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_user_id", sa.Uuid(), nullable=False),
        sa.Column("event", sa.String(length=24), nullable=False),
        sa.Column("ticket_version", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version > 0 AND ticket_version > 0", name="helpdesk_notice_version"),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["ticket_id", "organization_id"],
            ["helpdesk_tickets.id", "helpdesk_tickets.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_id", "recipient_user_id", "event", "ticket_version"),
    )
    op.create_index(
        "ix_helpdesk_notice_inbox",
        "helpdesk_notices",
        ["organization_id", "recipient_user_id", "id"],
        unique=False,
    )
    op.create_table(
        "helpdesk_attachments",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=120), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "size_bytes BETWEEN 1 AND 32768 AND size_bytes = octet_length(content)",
            name="helpdesk_attachment_size",
        ),
        sa.ForeignKeyConstraint(
            ["message_id", "ticket_id", "organization_id"],
            [
                "helpdesk_messages.id",
                "helpdesk_messages.ticket_id",
                "helpdesk_messages.organization_id",
            ],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_helpdesk_attachment_message",
        "helpdesk_attachments",
        ["organization_id", "ticket_id", "message_id"],
        unique=False,
    )
    install_guards()


def downgrade() -> None:
    op.execute("""
        DELETE FROM role_permissions WHERE permission_code IN
          ('ticket.view','ticket.assign','ticket.update','ticket.admin');
        DELETE FROM permissions WHERE code IN
          ('ticket.view','ticket.assign','ticket.update','ticket.admin');
    """)
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("ix_helpdesk_attachment_message", table_name="helpdesk_attachments")
    op.drop_table("helpdesk_attachments")
    op.drop_index("ix_helpdesk_notice_inbox", table_name="helpdesk_notices")
    op.drop_table("helpdesk_notices")
    op.drop_index("ix_helpdesk_messages", table_name="helpdesk_messages")
    op.drop_table("helpdesk_messages")
    op.drop_index("ix_helpdesk_history", table_name="helpdesk_history")
    op.drop_table("helpdesk_history")
    op.drop_table("helpdesk_assignments")
    op.drop_index("ix_helpdesk_queue", table_name="helpdesk_tickets")
    op.drop_index("ix_helpdesk_owner", table_name="helpdesk_tickets")
    op.drop_table("helpdesk_tickets")
    op.drop_table("helpdesk_preferences")
    op.execute("""
        DROP FUNCTION helpdesk_attachment_guard();
        DROP FUNCTION helpdesk_preference_guard();
        DROP FUNCTION helpdesk_notice_guard();
        DROP FUNCTION helpdesk_ticket_history_required();
        DROP FUNCTION helpdesk_ticket_guard();
        DROP FUNCTION helpdesk_immutable();
    """)
    # ### end Alembic commands ###
