import logging

from app.core.logging import configure_logging


def test_access_logs_do_not_record_private_download_capabilities(caplog):
    access = logging.getLogger("uvicorn.access")
    original = access.disabled
    try:
        configure_logging()
        caplog.set_level(logging.INFO)
        access.info("GET /exports/synthetic/download/synthetic-capability-canary 200")
        logging.getLogger("edp.test").info("request_completed status=200")
        assert "synthetic-capability-canary" not in caplog.text
        assert "request_completed status=200" in caplog.text
    finally:
        access.disabled = original
