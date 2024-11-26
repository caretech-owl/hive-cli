from datetime import datetime
from pathlib import Path
from typing import Any
from pydantic import BaseModel, computed_field
import yaml

class ComposerService(BaseModel):
    image: str | None = None
    build: str | None = None
    ports: list[str] | None = None
    volumes: list[str] | None = None
    environment: dict | None = None
    depends_on: list[str] | None = None

class ComposerConfig(BaseModel):
    services: dict[str, ComposerService] = {}

    @computed_field
    @property
    def images(self) -> list[str]:
        return [service.image for service in self.services.values() if service.image]

class Endpoint(BaseModel):
    name: str
    port: int
    protocol: str = "http"

class Recipe(BaseModel):
    path: Path
    compose: list[str] = []
    endpoints: list[Endpoint] = []
    config: ComposerConfig = ComposerConfig()
    environment: dict[str, str] = {}

    def model_post_init(self, __context: Any) -> None:
        for file in self.compose:
            with (self.path.parent / file).open() as f:
                config = ComposerConfig.model_validate(yaml.safe_load(f))
                self.config.services.update(config.services)

class HiveData(BaseModel):
    local_version: datetime
    remote_version: datetime
    recipe: Recipe | None
