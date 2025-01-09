import logging

from hive_cli.config import load_settings
from hive_cli.controller import Controller
from hive_cli.data import HiveData
from hive_cli.frontend import Frontend
from hive_cli.server import setup_logging

_LOGGER = logging.getLogger(__name__)

setup_logging()
settings = load_settings()
_LOGGER.info("Starting server in development mode.")
hive = HiveData(settings=settings)
frontend = Frontend(hive)
controller = Controller(frontend, hive)
frontend.setup_ui()
controller.update()
controller.update_logs()
