import logging
import uvicorn
from fastapi import FastAPI

from hive_cli.config import load_settings
from hive_cli.frontend import setup_ui

_LOGGER = logging.getLogger(__name__)

def run():
    server_settings = load_settings().server
    # you need to create the FastAPI app yourself
    app = FastAPI()
    setup_ui(app)

    if not server_settings.ssl.cert_path.exists():
        from hive_cli.ssl import generate_cert
        
        _LOGGER.info("No SSL certificate found. Generating a new one.")
        generate_cert()
    
    _LOGGER.info("Starting server.")
    # start uvicorn with the app
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=443,
        ssl_keyfile=server_settings.ssl.key_path,
        ssl_certfile=server_settings.ssl.cert_path,
        ssl_keyfile_password=server_settings.ssl.passphrase,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    run()
