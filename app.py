import logging
import uvicorn
from fastapi import FastAPI

from hive_cli.config import SSL_CERT_PATH, SSL_KEY_PATH
from hive_cli.frontend import setup_ui

_LOGGER = logging.getLogger(__name__)

def run():
    # you need to create the FastAPI app yourself
    app = FastAPI()
    setup_ui(app)

    if not SSL_CERT_PATH.exists():
        from hive_cli.ssl import generate_cert
        
        _LOGGER.info("No SSL certificate found. Generating a new one.")
        generate_cert()
    
    _LOGGER.info("Starting server.")
    # start uvicorn with the app
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=443,
        ssl_keyfile=SSL_KEY_PATH,
        ssl_certfile=SSL_CERT_PATH,
        ssl_keyfile_password=b"passphrase",
    )


if __name__ == "__main__":
    run()
