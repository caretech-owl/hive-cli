import logging

import hive_cli.server

_LOGGER = logging.getLogger(__name__)

# TODO: #2 Startup flow should be more interactive @aleneum
# - check if config exists
# - if config exists show a login screen via HTTPS
# - if no config exists show a setup screen via HTTP
#   - generate a new config and SSL certificate
#   - show fingerprint and reload setup page
#   - show password once!
logging.basicConfig()
_LOGGER.info("Starting hive-cli")
# start_prod()
hive_cli.server.dev()
