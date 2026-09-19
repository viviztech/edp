"""cms editorial content"""
from alembic import op
import sqlalchemy as sa
revision="3c4d5e6f7081"; down_revision="2b3fcc875606"; branch_labels=None; depends_on=None
def upgrade():
 op.create_table("cms_editorial_entries",
  sa.Column("organization_id",sa.Uuid(),nullable=False),sa.Column("kind",sa.String(20),nullable=False),sa.Column("slug",sa.String(120),nullable=False),sa.Column("locale",sa.String(2),nullable=False),sa.Column("state",sa.String(16),nullable=False),sa.Column("version",sa.Integer(),nullable=False),sa.Column("title",sa.String(200),nullable=False),sa.Column("body",sa.Text(),nullable=False),sa.Column("starts_at",sa.DateTime(timezone=True)),sa.Column("ends_at",sa.DateTime(timezone=True)),sa.Column("sort_order",sa.Integer(),nullable=False),sa.Column("published_at",sa.DateTime(timezone=True)),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),sa.Column("id",sa.Uuid(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
  sa.CheckConstraint("kind IN ('news','event','faq','testimonial')",name="cms_editorial_kind"),sa.CheckConstraint("locale IN ('en','ta')",name="cms_editorial_locale"),sa.CheckConstraint("state IN ('draft','published','archived')",name="cms_editorial_state"),sa.CheckConstraint("length(trim(title)) > 0 AND length(body) BETWEEN 1 AND 50000",name="cms_editorial_content"),sa.ForeignKeyConstraint(["organization_id"],["organizations.id"],ondelete="RESTRICT"),sa.PrimaryKeyConstraint("id"),sa.UniqueConstraint("organization_id","kind","slug","locale"))
 op.create_index("ix_cms_editorial_entries_organization_id","cms_editorial_entries",["organization_id"])
 op.create_index("ix_cms_editorial_public","cms_editorial_entries",["organization_id","kind","locale","state","sort_order"])
def downgrade():
 op.drop_index("ix_cms_editorial_public",table_name="cms_editorial_entries"); op.drop_index("ix_cms_editorial_entries_organization_id",table_name="cms_editorial_entries"); op.drop_table("cms_editorial_entries")
