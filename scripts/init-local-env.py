"""Create ignored local environment files without printing their secrets."""

import secrets
from pathlib import Path

from cryptography.fernet import Fernet

root = Path(__file__).resolve().parents[1]
paths = [root / ".env", root / "apps/api/.env", root / "apps/web/.env.local"]
if any(path.exists() for path in paths):
    raise SystemExit(
        "Refusing to overwrite existing environment files. Edit them explicitly."
    )
password = secrets.token_urlsafe(32)
bff = secrets.token_urlsafe(32)
key = Fernet.generate_key().decode()
meta_key = Fernet.generate_key().decode()
paths[0].write_text(
    f"POSTGRES_DB=edp_dev\nPOSTGRES_USER=edp_dev\nPOSTGRES_PASSWORD={password}\nBFF_KEY={bff}\nAUTH_DELIVERY_KEY={key}\nMETA_SECRET_KEY={meta_key}\nMETA_GRAPH_API_VERSION=\nMETA_EVENT_RETENTION_DAYS=\n"
)
paths[1].write_text(
    f"APP_ENV=local\nDATABASE_URL=postgresql+psycopg://edp_dev:{password}@localhost:5432/edp_dev\nREDIS_URL=redis://localhost:6379/0\nBFF_KEY={bff}\nAUTH_DELIVERY_KEY={key}\nMETA_SECRET_KEY={meta_key}\nMETA_GRAPH_API_VERSION=\nMETA_EVENT_RETENTION_DAYS=\n"
)
paths[2].write_text(
    f"API_INTERNAL_URL=http://localhost:8000\nWEB_ORIGIN=http://localhost:3000\nBFF_KEY={bff}\nCOOKIE_SECURE=false\n"
)
print("Created ignored local environment files. No credentials printed.")
