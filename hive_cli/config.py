from pathlib import Path
import uuid
from pydantic import BaseModel

CONFIG_PATH = Path.home() / '.hive-cli'
if not CONFIG_PATH.exists():
    CONFIG_PATH.mkdir()

SSL_KEY_PATH = CONFIG_PATH / 'key.pem'
SSL_CERT_PATH = CONFIG_PATH / 'cert.pem'
HIVE_REPO = CONFIG_PATH / 'hive'
HIVE_URL = "https://github.com/caretech-owl/hive.git"
CLI_CONFIG = CONFIG_PATH / 'config.json'


class SslConfig(BaseModel):
    organization_name = "CareTech OWL"
    common_name = "caretech-owl.de"
    country_name = "DE"
    state_or_province_name = "NRW"
    passphrase: str | None = None

class ServerConfig(BaseModel):
    ssl: SslConfig | None = None


class Settings(BaseModel):
    hive_uuid: uuid.UUID = uuid.UUID(int=uuid.getnode())
    update_interval: int = 60
    version: str = "0.0.0"
    server: ServerConfig | None = None


class _Instance:
    settings: Settings | None = None


def load_settings() -> Settings:
    if _Instance.settings is None:
        if not CLI_CONFIG.exists():
            with CLI_CONFIG.open('w') as f:
                f.write(Settings().model_dump_json(indent=2))
        with CLI_CONFIG.open() as f:
            _Instance.settings = Settings.model_validate_json(f.read())
    return _Instance.settings
