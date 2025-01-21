import logging
import logging.handlers
import os
import sys

import uvicorn
from fastapi import FastAPI

from hive_cli.config import load_settings
from hive_cli.controller import Controller
from hive_cli.data import HiveData
from hive_cli.frontend import Frontend
from hive_cli.ssl import get_sha256_fingerprint

_LOGGER = logging.getLogger(__name__)

# TODO: #2 Startup flow should be more interactive @aleneum
# - check if config exists
# - if config exists show a login screen via HTTPS
# - if no config exists show a setup screen via HTTP
#   - generate a new config and SSL certificate
#   - show fingerprint and reload setup page
#   - show password once!


def setup_logging() -> None:
    logging.basicConfig(level=logging.WARNING)
    settings = load_settings()
    logger = logging.getLogger("hive_cli")
    logger.setLevel(settings.log_level.upper())
    if settings.log_path:
        log_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        file_handler = logging.handlers.RotatingFileHandler(
            settings.log_path, encoding="utf-8", maxBytes=1048576, backupCount=10
        )
        file_handler.setFormatter(log_formatter)
        buffer_handler = logging.handlers.MemoryHandler(capacity=500)
        buffer_handler.setFormatter(log_formatter)
        logger.addHandler(file_handler)
        logger.addHandler(buffer_handler)


def prod() -> None:
    settings = load_settings()
    setup_logging()

    if not settings.server.ssl.cert_path.exists():
        from hive_cli.ssl import generate_cert

        _LOGGER.info("No SSL certificate found. Generating a new one.")
        generate_cert()

    _LOGGER.info("Cert Fingerprint: %s", get_sha256_fingerprint())
    hive = HiveData(settings=settings)
    app = FastAPI()
    frontend = Frontend(hive, app)
    with Controller(frontend, hive):
        frontend.setup_ui()
        _LOGGER.info("Starting server.")
        uvicorn.run(
            app,
            host=os.getenv("HIVE_HOST", "localhost"),
            port=int(os.getenv("HIVE_PORT", 12121)),
            ssl_keyfile=settings.server.ssl.key_path,
            ssl_certfile=settings.server.ssl.cert_path,
            ssl_keyfile_password=settings.server.ssl.passphrase,
            timeout_graceful_shutdown=1,
        )
    _LOGGER.info("Shutting down.")
    if (settings.hive_repo.parent / "_restart").exists():
        (settings.hive_repo.parent / "_restart").unlink()
        _LOGGER.info("Restarting hive-cli requested.")
        sys.exit(3)
    sys.exit(0)
