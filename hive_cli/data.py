import logging
from datetime import datetime
from pathlib import Path

import yaml
from pydantic import BaseModel, computed_field, field_serializer

_LOGGER = logging.getLogger(__name__)


class ComposerService(BaseModel):
    image: str | None = None
    build: str | None = None
    ports: list[str] | None = None
    volumes: list[str] | None = None
    environment: dict | None = None
    depends_on: list[str] | None = None
    command: list[str] | None = None
    entrypoint: list[str] | None = None


class ComposerNetwork(BaseModel):
    name: str
    driver: str | None = None


class ComposerVolume(BaseModel):
    driver: str


class ComposerFile(BaseModel):
    services: dict[str, ComposerService]
    networks: dict[str, ComposerNetwork] | None = None
    volumes: dict[str, ComposerVolume] | None = None

    def save(self, path: Path) -> None:
        _LOGGER.info("Saving composer file to %s", path.absolute())
        with path.open("w") as f:
            f.write(yaml.dump(self.model_dump(exclude_none=True)))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def images(self) -> list[str]:
        return [service.image for service in self.services.values() if service.image]


class Endpoint(BaseModel):
    name: str
    port: int
    protocol: str = "http"
    icon: str | None = None


class Recipe(BaseModel):
    path: Path
    compose: list[str] = []
    endpoints: list[Endpoint] = []
    environment: dict[str, str] = {}

    @field_serializer("path")
    def serialize_path(self, path: Path) -> str:
        return path.absolute().as_posix()

    def composer_files(self) -> dict[Path, ComposerFile]:
        files = {}
        for local_path in self.compose:
            path = (self.path.parent / local_path).resolve()
            if not path.exists():
                _LOGGER.warning("File %s not found.", path)
                continue
            with path.open("r") as f:
                yaml_obj = yaml.safe_load(f)
                files[path] = ComposerFile.model_validate(yaml_obj)
        return files

    def save(self) -> None:
        _LOGGER.info("Saving recipe to %s", self.path.absolute())
        with self.path.open("w") as f:
            f.write(yaml.dump(self.model_dump(exclude_none=True)))


class HiveData(BaseModel):
    local_version: datetime
    remote_version: datetime
    local_changes: bool = False
    recipe: Recipe | None
