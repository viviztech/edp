from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import get_settings
from app.core.database import Base
from app.modules.applications import models as application_models  # noqa: F401
from app.modules.attendance import models as attendance_models  # noqa: F401
from app.modules.business_plans import models as business_plan_models  # noqa: F401
from app.modules.businesses import models as business_models  # noqa: F401
from app.modules.cms import models as cms_models  # noqa: F401
from app.modules.crm import models as crm_models  # noqa: F401
from app.modules.files import models as file_models  # noqa: F401
from app.modules.helpdesk import models as helpdesk_models  # noqa: F401
from app.modules.identity import models as identity_models  # noqa: F401
from app.modules.knowledge import models as knowledge_models  # noqa: F401
from app.modules.lms import models as lms_models  # noqa: F401
from app.modules.mentoring import models as mentoring_models  # noqa: F401
from app.modules.meta import models as meta_models  # noqa: F401
from app.modules.notifications import models as notification_models  # noqa: F401
from app.modules.programs import models as program_models  # noqa: F401
from app.modules.reports import models as report_models  # noqa: F401
from app.modules.selection import models as selection_models  # noqa: F401

target_metadata = Base.metadata
url = get_settings().database_url.get_secret_value()

if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    with create_engine(url, poolclass=pool.NullPool).connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
