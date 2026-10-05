"""mentoring profiles, assignments, sessions and outcomes

Revision ID: a6c2d8e4f901
Revises: e5d1a7b9c234
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a6c2d8e4f901"
down_revision: str | None = "e5d1a7b9c234"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
    INSERT INTO permissions (code) VALUES
      ('mentoring.view'),('mentoring.manage'),('mentoring.admin')
    ON CONFLICT DO NOTHING;
    INSERT INTO role_permissions (role_id, permission_code)
    SELECT r.id, p.code FROM roles r CROSS JOIN permissions p
    WHERE ((r.name IN ('Super Admin','Program Director','Program Manager')
            AND p.code IN ('mentoring.view','mentoring.manage','mentoring.admin'))
        OR (r.name = 'Mentor' AND p.code IN ('mentoring.view','mentoring.manage'))
        OR (r.name = 'Participant' AND p.code = 'mentoring.view'))
    ON CONFLICT DO NOTHING;

    CREATE TABLE mentor_profiles (
      organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
      user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
      headline varchar(160) NOT NULL, biography text,
      state varchar(16) NOT NULL DEFAULT 'active', version integer NOT NULL DEFAULT 1,
      updated_at timestamptz NOT NULL, id uuid PRIMARY KEY, created_at timestamptz NOT NULL,
      CONSTRAINT uq_mentor_profile_user UNIQUE (organization_id,user_id),
      CONSTRAINT uq_mentor_profile_scope UNIQUE (id,organization_id),
      CONSTRAINT mentor_profile_state CHECK (state IN ('active','inactive')),
      CONSTRAINT mentor_profile_version CHECK (version > 0));
    CREATE INDEX ix_mentor_profiles_organization_id ON mentor_profiles(organization_id);
    CREATE INDEX ix_mentor_profiles_user_id ON mentor_profiles(user_id);

    CREATE TABLE mentor_expertise (
      organization_id uuid NOT NULL, mentor_profile_id uuid NOT NULL,
      code varchar(60) NOT NULL, name_en varchar(120) NOT NULL, name_ta varchar(120) NOT NULL,
      id uuid PRIMARY KEY, created_at timestamptz NOT NULL,
      CONSTRAINT fk_mentor_expertise_profile FOREIGN KEY (mentor_profile_id,organization_id)
        REFERENCES mentor_profiles(id,organization_id) ON DELETE RESTRICT,
      CONSTRAINT uq_mentor_expertise_code UNIQUE (mentor_profile_id,code),
      CONSTRAINT uq_mentor_expertise_scope UNIQUE (id,organization_id));
    CREATE INDEX ix_mentor_expertise_mentor_profile_id ON mentor_expertise(mentor_profile_id);
    CREATE INDEX ix_mentor_expertise_organization_id ON mentor_expertise(organization_id);

    CREATE TABLE mentor_availability (
      organization_id uuid NOT NULL, mentor_profile_id uuid NOT NULL,
      weekday integer NOT NULL, starts_at time NOT NULL, ends_at time NOT NULL,
      timezone varchar(64) NOT NULL DEFAULT 'Asia/Kolkata',
      id uuid PRIMARY KEY, created_at timestamptz NOT NULL,
      CONSTRAINT fk_mentor_availability_profile FOREIGN KEY (mentor_profile_id,organization_id)
        REFERENCES mentor_profiles(id,organization_id) ON DELETE RESTRICT,
      CONSTRAINT uq_mentor_availability UNIQUE (mentor_profile_id,weekday,starts_at,ends_at),
      CONSTRAINT mentor_availability_weekday CHECK (weekday BETWEEN 0 AND 6),
      CONSTRAINT mentor_availability_range CHECK (ends_at > starts_at));
    CREATE INDEX ix_mentor_availability_mentor_profile_id ON mentor_availability(mentor_profile_id);
    CREATE INDEX ix_mentor_availability_organization_id ON mentor_availability(organization_id);

    CREATE TABLE mentor_assignments (
      organization_id uuid NOT NULL, mentor_profile_id uuid NOT NULL, enrollment_id uuid NOT NULL,
      starts_on date NOT NULL, ends_on date, state varchar(16) NOT NULL DEFAULT 'active',
      assigned_by_user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
      ended_at timestamptz, version integer NOT NULL DEFAULT 1, updated_at timestamptz NOT NULL,
      id uuid PRIMARY KEY, created_at timestamptz NOT NULL,
      CONSTRAINT fk_mentor_assignment_profile FOREIGN KEY (mentor_profile_id,organization_id)
        REFERENCES mentor_profiles(id,organization_id) ON DELETE RESTRICT,
      CONSTRAINT fk_mentor_assignment_enrollment FOREIGN KEY (enrollment_id,organization_id)
        REFERENCES enrollments(id,organization_id) ON DELETE RESTRICT,
      CONSTRAINT uq_mentor_assignment_scope UNIQUE (id,organization_id),
      CONSTRAINT mentor_assignment_state CHECK (state IN ('active','ended')),
      CONSTRAINT mentor_assignment_dates CHECK (ends_on IS NULL OR ends_on >= starts_on),
      CONSTRAINT mentor_assignment_version CHECK (version > 0));
    CREATE INDEX ix_mentor_assignments_mentor_profile_id ON mentor_assignments(mentor_profile_id);
    CREATE INDEX ix_mentor_assignments_enrollment_id ON mentor_assignments(enrollment_id);
    CREATE INDEX ix_mentor_assignments_organization_id ON mentor_assignments(organization_id);
    CREATE UNIQUE INDEX uq_mentor_assignment_active_enrollment ON mentor_assignments(enrollment_id)
      WHERE state = 'active';

    CREATE TABLE mentoring_sessions (
      organization_id uuid NOT NULL, assignment_id uuid NOT NULL,
      starts_at timestamptz NOT NULL, ends_at timestamptz NOT NULL,
      mode varchar(16) NOT NULL, location_or_link varchar(500), topic varchar(240) NOT NULL,
      status varchar(16) NOT NULL DEFAULT 'scheduled', completed_at timestamptz,
      cancelled_at timestamptz, version integer NOT NULL DEFAULT 1, updated_at timestamptz NOT NULL,
      id uuid PRIMARY KEY, created_at timestamptz NOT NULL,
      CONSTRAINT fk_mentoring_session_assignment FOREIGN KEY (assignment_id,organization_id)
        REFERENCES mentor_assignments(id,organization_id) ON DELETE RESTRICT,
      CONSTRAINT uq_mentoring_session_scope UNIQUE (id,organization_id),
      CONSTRAINT mentoring_session_range CHECK (ends_at > starts_at),
      CONSTRAINT mentoring_session_mode CHECK (mode IN ('in_person','online','phone')),
      CONSTRAINT mentoring_session_status CHECK (status IN ('scheduled','completed','cancelled')),
      CONSTRAINT mentoring_session_version CHECK (version > 0));
    CREATE INDEX ix_mentoring_sessions_assignment_id ON mentoring_sessions(assignment_id);
    CREATE INDEX ix_mentoring_sessions_organization_id ON mentoring_sessions(organization_id);
    CREATE INDEX ix_mentoring_session_schedule
      ON mentoring_sessions(organization_id,starts_at,status);

    CREATE TABLE mentoring_notes (
      organization_id uuid NOT NULL, assignment_id uuid NOT NULL, session_id uuid,
      author_user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
      visibility varchar(32) NOT NULL, body text NOT NULL,
      id uuid PRIMARY KEY, created_at timestamptz NOT NULL,
      CONSTRAINT fk_mentoring_note_assignment FOREIGN KEY (assignment_id,organization_id)
        REFERENCES mentor_assignments(id,organization_id) ON DELETE RESTRICT,
      CONSTRAINT fk_mentoring_note_session FOREIGN KEY (session_id,organization_id)
        REFERENCES mentoring_sessions(id,organization_id) ON DELETE RESTRICT,
      CONSTRAINT mentoring_note_visibility
        CHECK (visibility IN ('mentor_private','shared_with_participant')));
    CREATE INDEX ix_mentoring_note_assignment ON mentoring_notes(assignment_id,created_at,id);
    CREATE INDEX ix_mentoring_notes_assignment_id ON mentoring_notes(assignment_id);
    CREATE INDEX ix_mentoring_notes_author_user_id ON mentoring_notes(author_user_id);
    CREATE INDEX ix_mentoring_notes_organization_id ON mentoring_notes(organization_id);
    CREATE INDEX ix_mentoring_notes_session_id ON mentoring_notes(session_id);

    CREATE TABLE mentoring_goals (
      organization_id uuid NOT NULL, assignment_id uuid NOT NULL, title varchar(240) NOT NULL,
      description text, target_date date, progress_percent integer NOT NULL DEFAULT 0,
      state varchar(16) NOT NULL DEFAULT 'active', completed_at timestamptz,
      version integer NOT NULL DEFAULT 1, updated_at timestamptz NOT NULL,
      id uuid PRIMARY KEY, created_at timestamptz NOT NULL,
      CONSTRAINT fk_mentoring_goal_assignment FOREIGN KEY (assignment_id,organization_id)
        REFERENCES mentor_assignments(id,organization_id) ON DELETE RESTRICT,
      CONSTRAINT uq_mentoring_goal_scope UNIQUE (id,organization_id),
      CONSTRAINT mentoring_goal_progress CHECK (progress_percent BETWEEN 0 AND 100),
      CONSTRAINT mentoring_goal_state CHECK (state IN ('active','completed','cancelled')),
      CONSTRAINT mentoring_goal_version CHECK (version > 0));
    CREATE INDEX ix_mentoring_goals_assignment_id ON mentoring_goals(assignment_id);
    CREATE INDEX ix_mentoring_goals_organization_id ON mentoring_goals(organization_id);

    CREATE TABLE mentoring_action_items (
      organization_id uuid NOT NULL, assignment_id uuid NOT NULL, goal_id uuid,
      title varchar(240) NOT NULL, due_at timestamptz, state varchar(16) NOT NULL DEFAULT 'open',
      completed_at timestamptz, version integer NOT NULL DEFAULT 1, updated_at timestamptz NOT NULL,
      id uuid PRIMARY KEY, created_at timestamptz NOT NULL,
      CONSTRAINT fk_mentoring_action_assignment FOREIGN KEY (assignment_id,organization_id)
        REFERENCES mentor_assignments(id,organization_id) ON DELETE RESTRICT,
      CONSTRAINT fk_mentoring_action_goal FOREIGN KEY (goal_id,organization_id)
        REFERENCES mentoring_goals(id,organization_id) ON DELETE RESTRICT,
      CONSTRAINT mentoring_action_state CHECK (state IN ('open','completed','cancelled')),
      CONSTRAINT mentoring_action_version CHECK (version > 0));
    CREATE INDEX ix_mentoring_action_items_assignment_id ON mentoring_action_items(assignment_id);
    CREATE INDEX ix_mentoring_action_items_goal_id ON mentoring_action_items(goal_id);
    CREATE INDEX ix_mentoring_action_items_organization_id
      ON mentoring_action_items(organization_id);

    CREATE TABLE mentoring_follow_ups (
      organization_id uuid NOT NULL, assignment_id uuid NOT NULL, session_id uuid,
      purpose varchar(240) NOT NULL, due_at timestamptz NOT NULL,
      state varchar(16) NOT NULL DEFAULT 'scheduled', completed_at timestamptz,
      version integer NOT NULL DEFAULT 1, updated_at timestamptz NOT NULL,
      id uuid PRIMARY KEY, created_at timestamptz NOT NULL,
      CONSTRAINT fk_mentoring_followup_assignment FOREIGN KEY (assignment_id,organization_id)
        REFERENCES mentor_assignments(id,organization_id) ON DELETE RESTRICT,
      CONSTRAINT fk_mentoring_followup_session FOREIGN KEY (session_id,organization_id)
        REFERENCES mentoring_sessions(id,organization_id) ON DELETE RESTRICT,
      CONSTRAINT mentoring_follow_up_state CHECK (state IN ('scheduled','completed','cancelled')),
      CONSTRAINT mentoring_follow_up_version CHECK (version > 0));
    CREATE INDEX ix_mentoring_follow_ups_assignment_id ON mentoring_follow_ups(assignment_id);
    CREATE INDEX ix_mentoring_follow_ups_session_id ON mentoring_follow_ups(session_id);
    CREATE INDEX ix_mentoring_follow_ups_organization_id ON mentoring_follow_ups(organization_id);
    CREATE INDEX ix_mentoring_follow_up_due ON mentoring_follow_ups(organization_id,state,due_at);

    CREATE TABLE mentoring_feedback (
      organization_id uuid NOT NULL, session_id uuid NOT NULL, participant_id uuid NOT NULL,
      rating integer NOT NULL, comment text, id uuid PRIMARY KEY, created_at timestamptz NOT NULL,
      CONSTRAINT fk_mentoring_feedback_session FOREIGN KEY (session_id,organization_id)
        REFERENCES mentoring_sessions(id,organization_id) ON DELETE RESTRICT,
      CONSTRAINT fk_mentoring_feedback_participant FOREIGN KEY (participant_id,organization_id)
        REFERENCES participants(id,organization_id) ON DELETE RESTRICT,
      CONSTRAINT uq_mentoring_feedback UNIQUE (session_id,participant_id),
      CONSTRAINT mentoring_feedback_rating CHECK (rating BETWEEN 1 AND 5));
    CREATE INDEX ix_mentoring_feedback_session_id ON mentoring_feedback(session_id);
    CREATE INDEX ix_mentoring_feedback_participant_id ON mentoring_feedback(participant_id);
    CREATE INDEX ix_mentoring_feedback_organization_id ON mentoring_feedback(organization_id);

    CREATE OR REPLACE FUNCTION reject_immutable_mentoring_rows() RETURNS trigger AS $$
    BEGIN RAISE EXCEPTION 'immutable mentoring evidence'; END; $$ LANGUAGE plpgsql;
    CREATE TRIGGER mentoring_notes_immutable BEFORE UPDATE OR DELETE ON mentoring_notes
      FOR EACH ROW EXECUTE FUNCTION reject_immutable_mentoring_rows();
    CREATE TRIGGER mentoring_feedback_immutable BEFORE UPDATE OR DELETE ON mentoring_feedback
      FOR EACH ROW EXECUTE FUNCTION reject_immutable_mentoring_rows();
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE mentoring_feedback;
    DROP TABLE mentoring_follow_ups;
    DROP TABLE mentoring_action_items;
    DROP TABLE mentoring_goals;
    DROP TABLE mentoring_notes;
    DROP TABLE mentoring_sessions;
    DROP TABLE mentor_assignments;
    DROP TABLE mentor_availability;
    DROP TABLE mentor_expertise;
    DROP TABLE mentor_profiles;
    DROP FUNCTION reject_immutable_mentoring_rows();
    DELETE FROM role_permissions WHERE permission_code LIKE 'mentoring.%';
    DELETE FROM permissions WHERE code LIKE 'mentoring.%';
    """)
