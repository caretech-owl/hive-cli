import logging
from hive_cli.config import load_settings
from hive_cli.docker import DockerController
from hive_cli.frontend import Frontend
from hive_cli.server import setup_logging

_LOGGER = logging.getLogger(__name__)

setup_logging()
settings = load_settings()
_LOGGER.info("Starting server in development mode.")
frontend = Frontend(settings, DockerController(settings))
frontend.setup_ui()
