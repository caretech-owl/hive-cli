import logging
import os
import random
import string
import uuid
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

_LOGGER = logging.getLogger(__name__)

CONFIG_PATH = Path(os.environ.get("HIVE_HOME", Path.home() / ".hive")).resolve()

if not CONFIG_PATH.exists():
    CONFIG_PATH.mkdir()

CLI_CONFIG = CONFIG_PATH / "config.json"


class SslConfig(BaseModel):
    key_path: Path = CONFIG_PATH / "key.pem"
    cert_path: Path = CONFIG_PATH / "cert.pem"
    organization_name: str = "CareTech OWL"
    common_name: str = "caretech-owl.de"
    country_name: str = "DE"
    locality_name: str = "Bielefeld"
    state_or_province_name: str = "NRW"
    passphrase: str = Field(
        default_factory=lambda: "".join(
            random.SystemRandom().choice(string.printable) for _ in range(32)
        )
    )


class ServerConfig(BaseModel):
    ssl: SslConfig = SslConfig()


class Settings(BaseModel):
    hive_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    hive_url: str = "https://github.com/caretech-owl/hive.git"
    hive_repo: Path = CONFIG_PATH / "hive"
    auto_update_recipe: bool = True
    update_interval: int = 600
    log_interval: int = 10
    version: str = "0.0.0"
    server: ServerConfig = ServerConfig()
    log_level: str = "DEBUG"
    log_path: Path | None = CONFIG_PATH / "hive.log"

    def save(self) -> None:
        _LOGGER.info("Saving settings to %s", CLI_CONFIG)
        with CLI_CONFIG.open("w") as f:
            f.write(self.model_dump_json(indent=2))


class _Instance:
    settings: Settings | None = None


def load_settings(reload: bool = False) -> Settings:
    if reload or _Instance.settings is None:
        if not CLI_CONFIG.exists():
            with CLI_CONFIG.open("w") as f:
                f.write(Settings().model_dump_json(indent=2))
        with CLI_CONFIG.open() as f:
            _Instance.settings = Settings.model_validate_json(f.read())
    return _Instance.settings
