import os

# No real credentials needed: unit probes replace the dependency check.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://localhost/edp_unit_unused")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
