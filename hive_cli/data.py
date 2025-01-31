import enum
import logging
from pathlib import Path

import yaml
from psygnal import EventedModel
from pydantic import BaseModel, Field, field_serializer

from hive_cli.config import Settings

_LOGGER = logging.getLogger(__name__)

COMPOSE_FILE_PATTERN = r"compose/[a-zA-Z0-9_-]+\.yml"


class ComposerService(BaseModel):
    image: str | None = None
    build: str | None = None
    ports: list[str] | None = None
    volumes: list[str] | None = None
    environment: dict | None = None
    depends_on: list[str] | None = None
    command: list[str] | None = None
    entrypoint: list[str] | None = None
    runtime: str | None = None


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
            obj = self.model_dump(exclude_none=True)
            f.write(yaml.dump(obj))

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

    def composer_files(self) -> dict[Path, ComposerFile | None]:
        files: dict[Path, ComposerFile | None] = {}
        for local_path in self.compose:
            path = (
                Path(local_path)
                if local_path.startswith("/")
                else self.path.parent / local_path
            ).resolve()
            if not path.exists():
                files[path] = None
                continue
            with path.open("r") as f:
                yaml_obj = yaml.safe_load(f)
                files[path] = ComposerFile.model_validate(yaml_obj)
        return files

    def save(self) -> None:
        _LOGGER.info("Saving recipe to %s", self.path.absolute())
        with self.path.open("w") as f:
            obj = self.model_dump(exclude_none=True)
            del obj["path"]
            f.write(yaml.dump(obj))


class RepoState(enum.Enum):
    UNKNOWN = enum.auto()
    NOT_FOUND = enum.auto()
    UP_TO_DATE = enum.auto()
    UPDATE_AVAILABLE = enum.auto()
    UPDATING = enum.auto()
    CHANGED_LOCALLY = enum.auto()
    CHANGES_COMMITTED = enum.auto()

class DockerState(enum.Enum):
    UNKNOWN = enum.auto()
    NOT_AVAILABLE = enum.auto()
    NOT_CONFIGURED = enum.auto()
    STOPPED = enum.auto()
    PULLING = enum.auto()
    STARTING = enum.auto()
    STARTED = enum.auto()
    STOPPING = enum.auto()


class ClientState(enum.Enum):
    UNKNOWN = enum.auto()
    UP_TO_DATE = enum.auto()
    UPDATE_AVAILABLE = enum.auto()
    UPDATING = enum.auto()
    RESTART_REQUIRED = enum.auto()


class ContainerState(BaseModel):
    command: str = Field(alias="Command")
    created_at: str = Field(alias="CreatedAt")
    exit_code: int = Field(alias="ExitCode")
    health: str = Field(alias="Health")
    id: str = Field(alias="ID")
    image: str = Field(alias="Image")
    local_volumes: str = Field(alias="LocalVolumes")
    mounts: str = Field(alias="Mounts")
    name: str = Field(alias="Name")
    # networks: str = Field(alias="Networks")
    # ports: str = Field(alias="Ports")
    status: str = Field(alias="Status")
    state: str = Field(alias="State")
    service: str = Field(alias="Service")


class HiveData(EventedModel):
    settings: Settings
    repo_state: RepoState = RepoState.UNKNOWN
    docker_state: DockerState = DockerState.UNKNOWN
    client_state: ClientState = ClientState.UNKNOWN
    container_states: list[ContainerState] = []
    container_logs: list[str] = []
    container_logs_num: int = 20
    client_logs: list[str] = []
    client_logs_num: int = 20
    recipe: Recipe | None = None
