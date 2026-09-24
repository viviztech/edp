"""Add interviews, panel scores, decisions, overrides and finalization."""

import sqlalchemy as sa
from alembic import op

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None

NEW_PERMISSIONS = (
    "selection.interview.manage",
    "selection.interview.score",
    "selection.decision.manage",
    "selection.decision.override",
    "selection.finalize",
)


def upgrade() -> None:
    for code in NEW_PERMISSIONS:
        op.execute(
            sa.text(
                "INSERT INTO permissions (code) VALUES (:code) ON CONFLICT DO NOTHING"
            ).bindparams(code=code)
        )
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_code)
        SELECT roles.id, permissions.code FROM roles CROSS JOIN permissions
        WHERE roles.name IN ('Super Admin', 'Program Director')
          AND permissions.code IN (
            'selection.interview.manage','selection.interview.score',
            'selection.decision.manage','selection.decision.override','selection.finalize'
          )
        ON CONFLICT DO NOTHING
    """)
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_code)
        SELECT roles.id, permissions.code FROM roles CROSS JOIN permissions
        WHERE roles.name = 'Program Manager'
          AND permissions.code IN ('selection.interview.manage','selection.decision.manage')
        ON CONFLICT DO NOTHING
    """)
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_code)
        SELECT roles.id, 'selection.interview.score' FROM roles
        WHERE roles.name = 'Selection Committee'
        ON CONFLICT DO NOTHING
    """)
    for constraint in (
        "application_history_to_state",
        "application_history_from_state",
    ):
        op.drop_constraint(constraint, "application_status_history", type_="check")
    op.create_check_constraint(
        "application_history_from_state",
        "application_status_history",
        "from_state IS NULL OR from_state IN "
        "('draft','submitted','under_review','shortlisted','interview_scheduled',"
        "'selected','waitlisted','rejected')",
    )
    op.create_check_constraint(
        "application_history_to_state",
        "application_status_history",
        "to_state IN ('draft','submitted','under_review','shortlisted',"
        "'interview_scheduled','selected','waitlisted','rejected')",
    )
    op.drop_constraint("application_submission_evidence", "applications", type_="check")
    op.drop_constraint("application_state", "applications", type_="check")
    op.create_check_constraint(
        "application_state",
        "applications",
        "state IN ('draft','submitted','under_review','shortlisted',"
        "'interview_scheduled','selected','waitlisted','rejected')",
    )
    op.create_check_constraint(
        "application_submission_evidence",
        "applications",
        "(state = 'draft' AND application_number IS NULL AND submitted_at IS NULL) OR "
        "(state <> 'draft' AND cycle_id IS NOT NULL AND application_number IS NOT NULL "
        "AND submitted_at IS NOT NULL)",
    )
    op.execute("DROP TRIGGER trg_application_submitted_immutable ON applications")
    op.execute("DROP FUNCTION protect_submitted_application")
    op.execute("""
        CREATE FUNCTION protect_submitted_application() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE' AND OLD.state <> 'draft' THEN
            RAISE EXCEPTION 'submitted application is immutable';
          END IF;
          IF OLD.state <> 'draft' AND NOT (
            NEW.version = OLD.version + 1
            AND NEW.id = OLD.id AND NEW.organization_id = OLD.organization_id
            AND NEW.person_id = OLD.person_id AND NEW.form_id = OLD.form_id
            AND NEW.cycle_id = OLD.cycle_id
            AND NEW.current_revision_id = OLD.current_revision_id
            AND NEW.application_number = OLD.application_number
            AND NEW.submitted_at = OLD.submitted_at AND NEW.created_at = OLD.created_at
            AND (
              (OLD.state = 'submitted' AND NEW.state = 'under_review')
              OR (OLD.state = 'under_review' AND NEW.state IN
                  ('shortlisted','selected','waitlisted','rejected'))
              OR (OLD.state = 'shortlisted' AND NEW.state IN
                  ('interview_scheduled','selected','waitlisted','rejected'))
              OR (OLD.state = 'interview_scheduled' AND NEW.state IN
                  ('selected','waitlisted','rejected'))
              OR (OLD.state IN ('selected','waitlisted','rejected')
                  AND NEW.state IN ('selected','waitlisted','rejected'))
            )
          ) THEN
            RAISE EXCEPTION 'submitted application evidence is immutable';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_application_submitted_immutable
        BEFORE UPDATE OR DELETE ON applications
        FOR EACH ROW EXECUTE FUNCTION protect_submitted_application();
    """)
    op.create_table(
        "interviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("selection_cycle_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("location", sa.String(500)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("average_score", sa.Numeric(7, 4)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id"),
        sa.UniqueConstraint("id", "organization_id"),
        sa.ForeignKeyConstraint(
            ["selection_cycle_id", "organization_id"],
            ["selection_cycles.id", "selection_cycles.organization_id"],
            name="fk_interview_cycle_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["application_id", "organization_id"],
            ["applications.id", "applications.organization_id"],
            name="fk_interview_application_scope",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("ends_at > starts_at", name="interview_time_range"),
        sa.CheckConstraint("mode IN ('online','in_person')", name="interview_mode"),
        sa.CheckConstraint("status IN ('scheduled','completed')", name="interview_status"),
        sa.CheckConstraint("(mode = 'online') OR location IS NOT NULL", name="interview_location"),
        sa.CheckConstraint(
            "(status = 'scheduled' AND average_score IS NULL AND completed_at IS NULL) OR "
            "(status = 'completed' AND average_score IS NOT NULL AND completed_at IS NOT NULL)",
            name="interview_completion",
        ),
        sa.CheckConstraint("version > 0", name="interview_version"),
    )
    op.create_index("ix_interviews_organization_id", "interviews", ["organization_id"])
    op.create_index("ix_interviews_selection_cycle_id", "interviews", ["selection_cycle_id"])
    op.create_index("ix_interviews_application_id", "interviews", ["application_id"])
    op.create_index(
        "ix_interview_cycle_status",
        "interviews",
        ["selection_cycle_id", "status", "starts_at"],
    )
    op.create_table(
        "interview_panel_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("interview_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Numeric(6, 2)),
        sa.Column("comment", sa.String(4000)),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("interview_id", "user_id"),
        sa.ForeignKeyConstraint(["interview_id"], ["interviews.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)", name="interview_panel_score"
        ),
        sa.CheckConstraint(
            "(score IS NULL AND submitted_at IS NULL) OR "
            "(score IS NOT NULL AND submitted_at IS NOT NULL)",
            name="interview_panel_submission",
        ),
        sa.CheckConstraint("version > 0", name="interview_panel_version"),
    )
    op.create_index(
        "ix_interview_panel_members_interview_id", "interview_panel_members", ["interview_id"]
    )
    op.create_index("ix_interview_panel_members_user_id", "interview_panel_members", ["user_id"])
    op.create_table(
        "selection_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("selection_cycle_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("from_state", sa.String(24), nullable=False),
        sa.Column("to_state", sa.String(24), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("is_override", sa.Boolean(), nullable=False),
        sa.Column("aggregate_score_snapshot", sa.Numeric(7, 2)),
        sa.Column("interview_score_snapshot", sa.Numeric(7, 2)),
        sa.Column("application_version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", "application_version"),
        sa.ForeignKeyConstraint(
            ["selection_cycle_id", "organization_id"],
            ["selection_cycles.id", "selection_cycles.organization_id"],
            name="fk_selection_decision_cycle_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["application_id", "organization_id"],
            ["applications.id", "applications.organization_id"],
            name="fk_selection_decision_application_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "from_state IN ('under_review','shortlisted','interview_scheduled',"
            "'selected','waitlisted','rejected')",
            name="selection_decision_from_state",
        ),
        sa.CheckConstraint(
            "to_state IN ('shortlisted','selected','waitlisted','rejected')",
            name="selection_decision_to_state",
        ),
        sa.CheckConstraint("application_version > 0", name="selection_decision_version"),
    )
    op.create_index(
        "ix_selection_decisions_organization_id", "selection_decisions", ["organization_id"]
    )
    op.create_index(
        "ix_selection_decisions_selection_cycle_id", "selection_decisions", ["selection_cycle_id"]
    )
    op.create_index(
        "ix_selection_decisions_application_id", "selection_decisions", ["application_id"]
    )
    op.create_index(
        "ix_selection_decisions_actor_user_id", "selection_decisions", ["actor_user_id"]
    )
    op.create_index(
        "ix_selection_decision_cycle_application",
        "selection_decisions",
        ["selection_cycle_id", "application_id", "created_at"],
    )
    op.execute("""
        CREATE FUNCTION protect_interview_panel_score() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE' AND OLD.submitted_at IS NOT NULL THEN
            RAISE EXCEPTION 'submitted interview score is immutable';
          END IF;
          IF OLD.submitted_at IS NOT NULL THEN
            RAISE EXCEPTION 'submitted interview score is immutable';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_interview_panel_score_immutable
        BEFORE UPDATE OR DELETE ON interview_panel_members
        FOR EACH ROW EXECUTE FUNCTION protect_interview_panel_score();

        CREATE FUNCTION protect_completed_interview() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.status = 'completed' THEN
            RAISE EXCEPTION 'completed interview is immutable';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_completed_interview_immutable
        BEFORE UPDATE OR DELETE ON interviews
        FOR EACH ROW EXECUTE FUNCTION protect_completed_interview();

        CREATE FUNCTION protect_selection_decision() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'selection decision history is immutable';
        END $$;
        CREATE TRIGGER trg_selection_decision_immutable
        BEFORE UPDATE OR DELETE ON selection_decisions
        FOR EACH ROW EXECUTE FUNCTION protect_selection_decision();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_selection_decision_immutable ON selection_decisions")
    op.execute("DROP FUNCTION protect_selection_decision")
    op.execute("DROP TRIGGER trg_completed_interview_immutable ON interviews")
    op.execute("DROP FUNCTION protect_completed_interview")
    op.execute("DROP TRIGGER trg_interview_panel_score_immutable ON interview_panel_members")
    op.execute("DROP FUNCTION protect_interview_panel_score")
    op.drop_index("ix_selection_decision_cycle_application", table_name="selection_decisions")
    op.drop_index("ix_selection_decisions_actor_user_id", table_name="selection_decisions")
    op.drop_index("ix_selection_decisions_application_id", table_name="selection_decisions")
    op.drop_index("ix_selection_decisions_selection_cycle_id", table_name="selection_decisions")
    op.drop_index("ix_selection_decisions_organization_id", table_name="selection_decisions")
    op.drop_table("selection_decisions")
    op.drop_index("ix_interview_panel_members_user_id", table_name="interview_panel_members")
    op.drop_index("ix_interview_panel_members_interview_id", table_name="interview_panel_members")
    op.drop_table("interview_panel_members")
    op.drop_index("ix_interview_cycle_status", table_name="interviews")
    op.drop_index("ix_interviews_application_id", table_name="interviews")
    op.drop_index("ix_interviews_selection_cycle_id", table_name="interviews")
    op.drop_index("ix_interviews_organization_id", table_name="interviews")
    op.drop_table("interviews")
    op.execute("DROP TRIGGER trg_application_submitted_immutable ON applications")
    op.execute("DROP FUNCTION protect_submitted_application")
    op.execute(
        "DROP TRIGGER trg_application_status_history_immutable ON application_status_history"
    )
    op.execute("DROP FUNCTION protect_application_status_history")
    op.execute(
        "DELETE FROM application_status_history WHERE to_state IN "
        "('shortlisted','interview_scheduled','selected','waitlisted','rejected')"
    )
    op.execute(
        "UPDATE applications SET state = 'under_review' WHERE state IN "
        "('shortlisted','interview_scheduled','selected','waitlisted','rejected')"
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
    op.execute("""
        CREATE FUNCTION protect_submitted_application() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'submitted application is immutable';
          END IF;
          IF OLD.state <> 'draft' AND NOT (
            OLD.state = 'submitted' AND NEW.state = 'under_review'
            AND NEW.version = OLD.version + 1
            AND NEW.id = OLD.id AND NEW.organization_id = OLD.organization_id
            AND NEW.person_id = OLD.person_id AND NEW.form_id = OLD.form_id
            AND NEW.cycle_id = OLD.cycle_id
            AND NEW.current_revision_id = OLD.current_revision_id
            AND NEW.application_number = OLD.application_number
            AND NEW.submitted_at = OLD.submitted_at AND NEW.created_at = OLD.created_at
          ) THEN
            RAISE EXCEPTION 'submitted application evidence is immutable';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_application_submitted_immutable
        BEFORE UPDATE OR DELETE ON applications
        FOR EACH ROW EXECUTE FUNCTION protect_submitted_application();
    """)
    op.drop_constraint("application_submission_evidence", "applications", type_="check")
    op.drop_constraint("application_state", "applications", type_="check")
    op.create_check_constraint(
        "application_state", "applications", "state IN ('draft','submitted','under_review')"
    )
    op.create_check_constraint(
        "application_submission_evidence",
        "applications",
        "(state = 'draft' AND application_number IS NULL AND submitted_at IS NULL) OR "
        "(state IN ('submitted','under_review') AND cycle_id IS NOT NULL "
        "AND application_number IS NOT NULL AND submitted_at IS NOT NULL)",
    )
    op.drop_constraint("application_history_to_state", "application_status_history", type_="check")
    op.drop_constraint(
        "application_history_from_state", "application_status_history", type_="check"
    )
    op.create_check_constraint(
        "application_history_from_state",
        "application_status_history",
        "from_state IS NULL OR from_state IN ('draft','submitted','under_review')",
    )
    op.create_check_constraint(
        "application_history_to_state",
        "application_status_history",
        "to_state IN ('draft','submitted','under_review')",
    )
    for code in NEW_PERMISSIONS:
        op.execute(
            sa.text("DELETE FROM role_permissions WHERE permission_code = :code").bindparams(
                code=code
            )
        )
        op.execute(sa.text("DELETE FROM permissions WHERE code = :code").bindparams(code=code))
