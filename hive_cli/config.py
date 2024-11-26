from pathlib import Path
import uuid
from pydantic import BaseModel, Field
import random
import string


CONFIG_PATH = Path.home() / ".hive-cli"
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
    state_or_province_name:str = "NRW"
    passphrase: str = Field(
        default_factory=lambda: "".join(
            random.SystemRandom().choice(string.printable) for _ in range(32)
        )
    )

class ServerConfig(BaseModel):
    ssl: SslConfig = SslConfig()


class Settings(BaseModel):
    hive_uuid: uuid.UUID = uuid.UUID(int=uuid.getnode())
    hive_url: str = "https://github.com/caretech-owl/hive.git"
    hive_repo: Path = CONFIG_PATH / "hive"
    update_interval: int = 60
    version: str = "0.0.0"
    server: ServerConfig = ServerConfig()


class _Instance:
    settings: Settings | None = None


def load_settings() -> Settings:
    if _Instance.settings is None:
        if not CLI_CONFIG.exists():
            with CLI_CONFIG.open("w") as f:
                f.write(Settings().model_dump_json(indent=2))
        with CLI_CONFIG.open() as f:
            _Instance.settings = Settings.model_validate_json(f.read())
    return _Instance.settings
