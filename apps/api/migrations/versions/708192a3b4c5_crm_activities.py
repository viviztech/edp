"""crm activities"""
from alembic import op
import sqlalchemy as sa
revision="708192a3b4c5"; down_revision="6f708192a3b4"; branch_labels=None; depends_on=None
def upgrade():
 op.create_table("crm_lead_activities",sa.Column("lead_id",sa.Uuid(),nullable=False),sa.Column("organization_id",sa.Uuid(),nullable=False),sa.Column("actor_user_id",sa.Uuid(),nullable=False),sa.Column("activity_type",sa.String(24),nullable=False),sa.Column("note",sa.Text(),nullable=False),sa.Column("due_at",sa.DateTime(timezone=True)),sa.Column("completed_at",sa.DateTime(timezone=True)),sa.Column("id",sa.Uuid(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.CheckConstraint("activity_type IN ('call','email','meeting','task','note')",name="crm_activity_type"),sa.CheckConstraint("length(trim(note)) BETWEEN 1 AND 5000",name="crm_activity_note"),sa.ForeignKeyConstraint(["lead_id"],["crm_leads.id"],ondelete="CASCADE"),sa.ForeignKeyConstraint(["organization_id"],["organizations.id"],ondelete="RESTRICT"),sa.ForeignKeyConstraint(["actor_user_id"],["users.id"],ondelete="RESTRICT"),sa.PrimaryKeyConstraint("id"))
 op.create_index("ix_crm_lead_activities_lead_id","crm_lead_activities",["lead_id"]); op.create_index("ix_crm_activity_queue","crm_lead_activities",["organization_id","lead_id","due_at"])
def downgrade():
 op.drop_index("ix_crm_activity_queue",table_name="crm_lead_activities"); op.drop_index("ix_crm_lead_activities_lead_id",table_name="crm_lead_activities"); op.drop_table("crm_lead_activities")
