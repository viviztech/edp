"""B01.1 enrollment-owned business-plan drafts and immutable revisions.

Revision ID: b7d3e9f5a012
Revises: a6c2d8e4f901
"""

from collections.abc import Sequence

from alembic import op

revision: str = "b7d3e9f5a012"
down_revision: str | None = "a6c2d8e4f901"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE business_plans (
      organization_id uuid NOT NULL,
      enrollment_id uuid NOT NULL,
      status varchar(24) NOT NULL DEFAULT 'draft',
      version integer NOT NULL DEFAULT 1,
      updated_at timestamptz NOT NULL,
      id uuid PRIMARY KEY,
      created_at timestamptz NOT NULL,
      CONSTRAINT fk_business_plan_enrollment FOREIGN KEY (enrollment_id, organization_id)
        REFERENCES enrollments(id, organization_id) ON DELETE RESTRICT,
      CONSTRAINT uq_business_plan_enrollment UNIQUE (enrollment_id),
      CONSTRAINT uq_business_plan_scope UNIQUE (id, organization_id),
      CONSTRAINT business_plan_status
        CHECK (status IN ('draft','submitted','changes_requested','approved')),
      CONSTRAINT business_plan_version CHECK (version > 0)
    );
    CREATE INDEX ix_business_plans_organization_id ON business_plans(organization_id);
    CREATE INDEX ix_business_plans_enrollment_id ON business_plans(enrollment_id);

    CREATE TABLE business_plan_revisions (
      organization_id uuid NOT NULL,
      plan_id uuid NOT NULL,
      version integer NOT NULL,
      section_code varchar(40) NOT NULL,
      body text NOT NULL,
      author_user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
      id uuid PRIMARY KEY,
      created_at timestamptz NOT NULL,
      CONSTRAINT fk_business_plan_revision_plan FOREIGN KEY (plan_id, organization_id)
        REFERENCES business_plans(id, organization_id) ON DELETE RESTRICT,
      CONSTRAINT uq_business_plan_revision UNIQUE (plan_id, version),
      CONSTRAINT business_plan_revision_version CHECK (version > 1),
      CONSTRAINT business_plan_revision_body_length CHECK (char_length(body) <= 10000)
    );
    CREATE INDEX ix_business_plan_revisions_organization_id
      ON business_plan_revisions(organization_id);
    CREATE INDEX ix_business_plan_revisions_plan_id ON business_plan_revisions(plan_id);

    CREATE FUNCTION reject_business_plan_revision_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'business plan revisions are immutable'; END;
    $$;
    CREATE TRIGGER business_plan_revision_immutable
      BEFORE UPDATE OR DELETE ON business_plan_revisions
      FOR EACH ROW EXECUTE FUNCTION reject_business_plan_revision_mutation();

    CREATE TABLE business_plan_submissions (
      organization_id uuid NOT NULL,
      plan_id uuid NOT NULL,
      number integer NOT NULL,
      snapshot jsonb NOT NULL,
      submitted_by_user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
      id uuid PRIMARY KEY,
      created_at timestamptz NOT NULL,
      CONSTRAINT fk_business_plan_submission_plan FOREIGN KEY (plan_id,organization_id)
        REFERENCES business_plans(id,organization_id) ON DELETE RESTRICT,
      CONSTRAINT uq_business_plan_submission_number UNIQUE (plan_id,number),
      CONSTRAINT uq_business_plan_submission_scope UNIQUE (id,organization_id),
      CONSTRAINT business_plan_submission_number CHECK (number > 0)
    );
    CREATE INDEX ix_business_plan_submissions_organization_id
      ON business_plan_submissions(organization_id);
    CREATE INDEX ix_business_plan_submissions_plan_id ON business_plan_submissions(plan_id);

    CREATE TABLE business_plan_reviews (
      organization_id uuid NOT NULL,
      submission_id uuid NOT NULL,
      reviewer_user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
      decision varchar(24) NOT NULL,
      comments jsonb NOT NULL,
      reason varchar(500) NOT NULL,
      id uuid PRIMARY KEY,
      created_at timestamptz NOT NULL,
      CONSTRAINT fk_business_plan_review_submission FOREIGN KEY (submission_id,organization_id)
        REFERENCES business_plan_submissions(id,organization_id) ON DELETE RESTRICT,
      CONSTRAINT uq_business_plan_review_submission UNIQUE (submission_id),
      CONSTRAINT business_plan_review_decision
        CHECK (decision IN ('changes_requested','approved'))
    );
    CREATE INDEX ix_business_plan_reviews_organization_id ON business_plan_reviews(organization_id);
    CREATE INDEX ix_business_plan_reviews_submission_id ON business_plan_reviews(submission_id);
    CREATE TRIGGER business_plan_submission_immutable
      BEFORE UPDATE OR DELETE ON business_plan_submissions
      FOR EACH ROW EXECUTE FUNCTION reject_business_plan_revision_mutation();
    CREATE TRIGGER business_plan_review_immutable
      BEFORE UPDATE OR DELETE ON business_plan_reviews
      FOR EACH ROW EXECUTE FUNCTION reject_business_plan_revision_mutation();
    """)


def downgrade() -> None:
    op.execute("""
    DROP TRIGGER business_plan_review_immutable ON business_plan_reviews;
    DROP TRIGGER business_plan_submission_immutable ON business_plan_submissions;
    DROP TABLE business_plan_reviews;
    DROP TABLE business_plan_submissions;
    DROP TRIGGER business_plan_revision_immutable ON business_plan_revisions;
    DROP FUNCTION reject_business_plan_revision_mutation();
    DROP TABLE business_plan_revisions;
    DROP TABLE business_plans;
    """)
