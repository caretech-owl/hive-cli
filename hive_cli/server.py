import logging
import logging.handlers
from fastapi import FastAPI
import uvicorn

from hive_cli.config import load_settings
from hive_cli.docker import DockerController
from hive_cli.frontend import Frontend

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
        logFormatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        fileHandler = logging.handlers.RotatingFileHandler(
            settings.log_path, encoding="utf-8", maxBytes=1048576, backupCount=10
        )
        fileHandler.setFormatter(logFormatter)
        bufferHandler = logging.handlers.MemoryHandler(capacity=500)
        bufferHandler.setFormatter(logFormatter)
        logger.addHandler(fileHandler)
        logger.addHandler(bufferHandler)


def prod() -> None:
    settings = load_settings()
    setup_logging()

    if not settings.server.ssl.cert_path.exists():
        from hive_cli.ssl import generate_cert

        _LOGGER.info("No SSL certificate found. Generating a new one.")
        generate_cert()

    app = FastAPI()
    frontend = Frontend(settings, DockerController(settings), app)
    frontend.setup_ui()

    _LOGGER.info("Starting server.")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=443,
        ssl_keyfile=settings.server.ssl.key_path,
        ssl_certfile=settings.server.ssl.cert_path,
        ssl_keyfile_password=settings.server.ssl.passphrase,
        timeout_graceful_shutdown=1,
    )
