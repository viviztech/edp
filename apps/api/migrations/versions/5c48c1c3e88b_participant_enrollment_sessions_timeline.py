"""Participant enrollment, sessions and timeline."""

# ruff: noqa: E501

import sqlalchemy as sa
from alembic import op

revision = "5c48c1c3e88b"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for code in (
        "participant.view",
        "participant.update",
        "enrollment.manage",
        "schedule.manage",
        "participant.self",
    ):
        op.execute(
            sa.text(
                "INSERT INTO permissions (code) VALUES (:code) ON CONFLICT DO NOTHING"
            ).bindparams(code=code)
        )
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_code)
        SELECT roles.id, permissions.code FROM roles CROSS JOIN permissions
        WHERE roles.name IN ('Super Admin', 'Program Director', 'Program Manager')
          AND permissions.code IN ('participant.view','participant.update','enrollment.manage','schedule.manage')
        ON CONFLICT DO NOTHING
    """)
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_code)
        SELECT roles.id, permissions.code FROM roles CROSS JOIN permissions
        WHERE roles.name = 'Participant' AND permissions.code IN ('system.access','participant.self')
        ON CONFLICT DO NOTHING
    """)
    for constraint in ("application_history_to_state", "application_history_from_state"):
        op.drop_constraint(constraint, "application_status_history", type_="check")
    op.create_check_constraint(
        "application_history_from_state",
        "application_status_history",
        "from_state IS NULL OR from_state IN ('draft','submitted','under_review','shortlisted','interview_scheduled','selected','waitlisted','rejected','enrolled')",
    )
    op.create_check_constraint(
        "application_history_to_state",
        "application_status_history",
        "to_state IN ('draft','submitted','under_review','shortlisted','interview_scheduled','selected','waitlisted','rejected','enrolled')",
    )
    op.drop_constraint("application_submission_evidence", "applications", type_="check")
    op.drop_constraint("application_state", "applications", type_="check")
    op.create_check_constraint(
        "application_state",
        "applications",
        "state IN ('draft','submitted','under_review','shortlisted','interview_scheduled','selected','waitlisted','rejected','enrolled')",
    )
    op.create_check_constraint(
        "application_submission_evidence",
        "applications",
        "(state = 'draft' AND application_number IS NULL AND submitted_at IS NULL) OR (state <> 'draft' AND cycle_id IS NOT NULL AND application_number IS NOT NULL AND submitted_at IS NOT NULL)",
    )
    op.execute("DROP TRIGGER trg_application_submitted_immutable ON applications")
    op.execute("DROP FUNCTION protect_submitted_application")
    op.execute("""
        CREATE FUNCTION protect_submitted_application() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE' AND OLD.state <> 'draft' THEN RAISE EXCEPTION 'submitted application is immutable'; END IF;
          IF OLD.state <> 'draft' AND NOT (
            NEW.version = OLD.version + 1 AND NEW.id = OLD.id
            AND NEW.organization_id = OLD.organization_id AND NEW.person_id = OLD.person_id
            AND NEW.form_id = OLD.form_id AND NEW.cycle_id = OLD.cycle_id
            AND NEW.current_revision_id = OLD.current_revision_id
            AND NEW.application_number = OLD.application_number
            AND NEW.submitted_at = OLD.submitted_at AND NEW.created_at = OLD.created_at
            AND ((OLD.state = 'submitted' AND NEW.state = 'under_review')
              OR (OLD.state = 'under_review' AND NEW.state IN ('shortlisted','selected','waitlisted','rejected'))
              OR (OLD.state = 'shortlisted' AND NEW.state IN ('interview_scheduled','selected','waitlisted','rejected'))
              OR (OLD.state = 'interview_scheduled' AND NEW.state IN ('selected','waitlisted','rejected'))
              OR (OLD.state IN ('selected','waitlisted','rejected') AND NEW.state IN ('selected','waitlisted','rejected'))
              OR (OLD.state = 'selected' AND NEW.state = 'enrolled'))
          ) THEN RAISE EXCEPTION 'submitted application evidence is immutable'; END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_application_submitted_immutable BEFORE UPDATE OR DELETE ON applications
        FOR EACH ROW EXECUTE FUNCTION protect_submitted_application();
    """)
    op.create_table(
        "domain_outbox",
        sa.Column("event_key", sa.String(length=160), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("aggregate_type", sa.String(length=40), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("payload", sa.String(length=1000), nullable=False),
        sa.Column("dispatched", sa.Boolean(), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(dispatched = false AND dispatched_at IS NULL) OR (dispatched = true AND dispatched_at IS NOT NULL)",
            name="domain_outbox_dispatch_state",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_key"),
    )
    op.create_index(
        op.f("ix_domain_outbox_aggregate_id"), "domain_outbox", ["aggregate_id"], unique=False
    )
    op.create_index(
        op.f("ix_domain_outbox_event_type"), "domain_outbox", ["event_type"], unique=False
    )
    op.create_index(
        op.f("ix_domain_outbox_organization_id"), "domain_outbox", ["organization_id"], unique=False
    )
    op.create_index(
        "ix_domain_outbox_pending",
        "domain_outbox",
        ["dispatched", "created_at", "id"],
        unique=False,
    )
    op.create_table(
        "participants",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('active','suspended','completed','withdrawn')", name="participant_status"
        ),
        sa.CheckConstraint("version > 0", name="participant_version"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id"),
        sa.UniqueConstraint("organization_id", "person_id"),
    )
    op.create_index(
        "ix_participant_scope_status",
        "participants",
        ["organization_id", "status", "id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_participants_organization_id"), "participants", ["organization_id"], unique=False
    )
    op.create_index(op.f("ix_participants_person_id"), "participants", ["person_id"], unique=False)
    op.create_table(
        "participant_status_history",
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", sa.String(length=16), nullable=True),
        sa.Column("to_status", sa.String(length=16), nullable=False),
        sa.Column("participant_version", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "from_status IS NULL OR from_status IN ('active','suspended','completed','withdrawn')",
            name="participant_history_from_status",
        ),
        sa.CheckConstraint(
            "to_status IN ('active','suspended','completed','withdrawn')",
            name="participant_history_to_status",
        ),
        sa.CheckConstraint("participant_version > 0", name="participant_history_version"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("participant_id", "participant_version"),
    )
    op.create_index(
        op.f("ix_participant_status_history_participant_id"),
        "participant_status_history",
        ["participant_id"],
        unique=False,
    )
    op.create_table(
        "program_sessions",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("cohort_id", sa.Uuid(), nullable=False),
        sa.Column("title_en", sa.String(length=200), nullable=False),
        sa.Column("title_ta", sa.String(length=200), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("location", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "mode = 'online' OR location IS NOT NULL", name="program_session_location"
        ),
        sa.CheckConstraint("mode IN ('in_person','online','hybrid')", name="program_session_mode"),
        sa.CheckConstraint(
            "status IN ('scheduled','completed','cancelled')", name="program_session_status"
        ),
        sa.CheckConstraint("ends_at > starts_at", name="program_session_time_range"),
        sa.CheckConstraint("version > 0", name="program_session_version"),
        sa.ForeignKeyConstraint(
            ["cohort_id", "organization_id"],
            ["cohorts.id", "cohorts.organization_id"],
            name="fk_program_session_cohort_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id"),
    )
    op.create_index(
        "ix_program_session_cohort_time",
        "program_sessions",
        ["cohort_id", "starts_at", "id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_program_sessions_cohort_id"), "program_sessions", ["cohort_id"], unique=False
    )
    op.create_index(
        op.f("ix_program_sessions_organization_id"),
        "program_sessions",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "enrollments",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("program_id", sa.Uuid(), nullable=False),
        sa.Column("cohort_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('active','completed','withdrawn')", name="enrollment_status"
        ),
        sa.CheckConstraint("version > 0", name="enrollment_version"),
        sa.ForeignKeyConstraint(
            ["application_id", "organization_id"],
            ["applications.id", "applications.organization_id"],
            name="fk_enrollment_application_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["cohort_id", "program_id", "organization_id"],
            ["cohorts.id", "cohorts.program_id", "cohorts.organization_id"],
            name="fk_enrollment_cohort_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["participant_id", "organization_id"],
            ["participants.id", "participants.organization_id"],
            name="fk_enrollment_participant_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["program_id", "organization_id"],
            ["programs.id", "programs.organization_id"],
            name="fk_enrollment_program_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id"),
        sa.UniqueConstraint("id", "organization_id"),
        sa.UniqueConstraint("participant_id", "cohort_id"),
    )
    op.create_index(
        "ix_enrollment_cohort_status", "enrollments", ["cohort_id", "status", "id"], unique=False
    )
    op.create_index(
        op.f("ix_enrollments_application_id"), "enrollments", ["application_id"], unique=False
    )
    op.create_index(op.f("ix_enrollments_cohort_id"), "enrollments", ["cohort_id"], unique=False)
    op.create_index(
        op.f("ix_enrollments_organization_id"), "enrollments", ["organization_id"], unique=False
    )
    op.create_index(
        op.f("ix_enrollments_participant_id"), "enrollments", ["participant_id"], unique=False
    )
    op.create_index(op.f("ix_enrollments_program_id"), "enrollments", ["program_id"], unique=False)
    op.execute("""
        CREATE FUNCTION protect_participant_history() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'participant status history is append-only'; END $$;
        CREATE TRIGGER trg_participant_history_immutable BEFORE UPDATE OR DELETE ON participant_status_history
        FOR EACH ROW EXECUTE FUNCTION protect_participant_history();
        CREATE FUNCTION protect_domain_outbox() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE' OR NEW.event_key <> OLD.event_key OR NEW.event_type <> OLD.event_type
             OR NEW.aggregate_type <> OLD.aggregate_type OR NEW.aggregate_id <> OLD.aggregate_id
             OR NEW.organization_id <> OLD.organization_id OR NEW.payload <> OLD.payload
             OR NEW.created_at <> OLD.created_at THEN
            RAISE EXCEPTION 'domain outbox evidence is immutable';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_domain_outbox_immutable BEFORE UPDATE OR DELETE ON domain_outbox
        FOR EACH ROW EXECUTE FUNCTION protect_domain_outbox();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_participant_history_immutable ON participant_status_history")
    op.execute("DROP FUNCTION protect_participant_history")
    op.execute("DROP TRIGGER trg_domain_outbox_immutable ON domain_outbox")
    op.execute("DROP FUNCTION protect_domain_outbox")
    op.execute("DROP TRIGGER trg_application_submitted_immutable ON applications")
    op.execute("DROP FUNCTION protect_submitted_application")
    op.execute(
        "DROP TRIGGER trg_application_status_history_immutable ON application_status_history"
    )
    op.execute("DROP FUNCTION protect_application_status_history")
    op.execute(
        "DELETE FROM application_status_history WHERE to_state = 'enrolled' OR from_state = 'enrolled'"
    )
    op.execute("""
        CREATE FUNCTION protect_application_status_history() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'application status history is immutable';
        END $$;
        CREATE TRIGGER trg_application_status_history_immutable
        BEFORE UPDATE OR DELETE ON application_status_history
        FOR EACH ROW EXECUTE FUNCTION protect_application_status_history();
    """)
    op.execute(
        "UPDATE applications SET state = 'selected', version = version + 1, updated_at = CURRENT_TIMESTAMP WHERE state = 'enrolled'"
    )
    op.drop_constraint("application_submission_evidence", "applications", type_="check")
    op.drop_constraint("application_state", "applications", type_="check")
    op.create_check_constraint(
        "application_state",
        "applications",
        "state IN ('draft','submitted','under_review','shortlisted','interview_scheduled','selected','waitlisted','rejected')",
    )
    op.create_check_constraint(
        "application_submission_evidence",
        "applications",
        "(state = 'draft' AND application_number IS NULL AND submitted_at IS NULL) OR (state <> 'draft' AND cycle_id IS NOT NULL AND application_number IS NOT NULL AND submitted_at IS NOT NULL)",
    )
    for constraint in ("application_history_to_state", "application_history_from_state"):
        op.drop_constraint(constraint, "application_status_history", type_="check")
    op.create_check_constraint(
        "application_history_from_state",
        "application_status_history",
        "from_state IS NULL OR from_state IN ('draft','submitted','under_review','shortlisted','interview_scheduled','selected','waitlisted','rejected')",
    )
    op.create_check_constraint(
        "application_history_to_state",
        "application_status_history",
        "to_state IN ('draft','submitted','under_review','shortlisted','interview_scheduled','selected','waitlisted','rejected')",
    )
    op.drop_index(op.f("ix_enrollments_program_id"), table_name="enrollments")
    op.drop_index(op.f("ix_enrollments_participant_id"), table_name="enrollments")
    op.drop_index(op.f("ix_enrollments_organization_id"), table_name="enrollments")
    op.drop_index(op.f("ix_enrollments_cohort_id"), table_name="enrollments")
    op.drop_index(op.f("ix_enrollments_application_id"), table_name="enrollments")
    op.drop_index("ix_enrollment_cohort_status", table_name="enrollments")
    op.drop_table("enrollments")
    op.drop_index(op.f("ix_program_sessions_organization_id"), table_name="program_sessions")
    op.drop_index(op.f("ix_program_sessions_cohort_id"), table_name="program_sessions")
    op.drop_index("ix_program_session_cohort_time", table_name="program_sessions")
    op.drop_table("program_sessions")
    op.drop_index(
        op.f("ix_participant_status_history_participant_id"),
        table_name="participant_status_history",
    )
    op.drop_table("participant_status_history")
    op.drop_index(op.f("ix_participants_person_id"), table_name="participants")
    op.drop_index(op.f("ix_participants_organization_id"), table_name="participants")
    op.drop_index("ix_participant_scope_status", table_name="participants")
    op.drop_table("participants")
    op.drop_index("ix_domain_outbox_pending", table_name="domain_outbox")
    op.drop_index(op.f("ix_domain_outbox_organization_id"), table_name="domain_outbox")
    op.drop_index(op.f("ix_domain_outbox_event_type"), table_name="domain_outbox")
    op.drop_index(op.f("ix_domain_outbox_aggregate_id"), table_name="domain_outbox")
    op.drop_table("domain_outbox")
    op.execute("""
        CREATE FUNCTION protect_submitted_application() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE' AND OLD.state <> 'draft' THEN RAISE EXCEPTION 'submitted application is immutable'; END IF;
          IF OLD.state <> 'draft' AND NOT (
            NEW.version = OLD.version + 1 AND NEW.id = OLD.id
            AND NEW.organization_id = OLD.organization_id AND NEW.person_id = OLD.person_id
            AND NEW.form_id = OLD.form_id AND NEW.cycle_id = OLD.cycle_id
            AND NEW.current_revision_id = OLD.current_revision_id
            AND NEW.application_number = OLD.application_number
            AND NEW.submitted_at = OLD.submitted_at AND NEW.created_at = OLD.created_at
            AND ((OLD.state = 'submitted' AND NEW.state = 'under_review')
              OR (OLD.state = 'under_review' AND NEW.state IN ('shortlisted','selected','waitlisted','rejected'))
              OR (OLD.state = 'shortlisted' AND NEW.state IN ('interview_scheduled','selected','waitlisted','rejected'))
              OR (OLD.state = 'interview_scheduled' AND NEW.state IN ('selected','waitlisted','rejected'))
              OR (OLD.state IN ('selected','waitlisted','rejected') AND NEW.state IN ('selected','waitlisted','rejected')))
          ) THEN RAISE EXCEPTION 'submitted application evidence is immutable'; END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_application_submitted_immutable BEFORE UPDATE OR DELETE ON applications
        FOR EACH ROW EXECUTE FUNCTION protect_submitted_application();
    """)
    op.execute("""
        DELETE FROM role_permissions WHERE permission_code IN ('participant.view','participant.update','enrollment.manage','schedule.manage','participant.self');
        DELETE FROM permissions WHERE code IN ('participant.view','participant.update','enrollment.manage','schedule.manage','participant.self');
    """)
