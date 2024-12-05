import logging
import docker
import subprocess
import enum
import time
import os

import docker.models
import docker.models.images
from pydantic import BaseModel, Field

from hive_cli.config import Settings
from hive_cli.data import Recipe

from threading import Thread


_LOGGER = logging.getLogger(__name__)


class DockerState(enum.Enum):
    UNKNOWN = enum.auto()
    NOT_AVAILABLE = enum.auto()
    NOT_CONFIGURED = enum.auto()
    STOPPED = enum.auto()
    PULLING = enum.auto()
    STARTING = enum.auto()
    STARTED = enum.auto()
    STOPPING = enum.auto()


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


class DockerController:

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.state = DockerState.NOT_CONFIGURED
        self.client = None
        self._runner = None
        self._recipe: Recipe | None = None
        try:
            self.client = docker.from_env()
        except Exception as e:
            _LOGGER.error(e)
            self.state = DockerState.NOT_AVAILABLE

    @property
    def recipe(self) -> Recipe | None:
        return self._recipe

    @recipe.setter
    def recipe(self, value: Recipe) -> None:
        if (
            self._recipe != value
            and self._recipe is not None
            and self.state == DockerState.STARTED
        ):
            _LOGGER.info("Stopping Docker Compose before changing recipe...")
            self.stop()
        self._recipe = value
        if value is None:
            self.state = DockerState.NOT_CONFIGURED
        else:
            self.state = (
                DockerState.STOPPED
                if len(self.get_container_states()) == 0
                else DockerState.STARTED
            )

    def get_container_states(self) -> list[ContainerState]:
        if self.recipe is None:
            return []

        cmd = ["docker", "compose"]
        for composer_file in self.recipe.compose:
            cmd.extend(["-f", composer_file])
        cmd.extend(["ps", "--format", "json"])
        _LOGGER.debug(f"Running command: {' '.join(cmd)}")
        res = subprocess.check_output(
            cmd, cwd=self.recipe.path.parent, env=os.environ | self.recipe.environment
        ).decode("utf-8")
        return [ContainerState.model_validate_json(line) for line in res.splitlines()]
    
    def get_container_logs(self, num_entries: int) -> list[str]:
        if self.recipe is None:
            return []

        lines = []
        for line in self.compose_do("logs", "--no-color", "-n", str(num_entries)).stdout:
            lines.append(line.decode("utf-8").strip())
        return lines

    def _task_start(self) -> None:
        for image_name in self.recipe.config.images:
            _LOGGER.info(f"Pulling image: {image_name}")
            pipe = self.compose_do("pull")
            for line in pipe.stdout:
                _LOGGER.debug(line.decode("utf-8").strip())
        _LOGGER.info("Starting Docker Compose")
        self.state = DockerState.STARTING
        pipe = self.compose_do("up", "-d")
        for line in pipe.stdout:
            _LOGGER.debug(line.decode("utf-8").strip())
        self.state = DockerState.STARTED

    def _task_stop(self) -> None:
        _LOGGER.info("Stopping Docker Compose")
        pipe = self.compose_do("down")
        for line in pipe.stdout:
            _LOGGER.debug(line.decode("utf-8").strip())
        self.state = DockerState.STOPPED

    def start(self) -> None:
        if self.state == DockerState.STOPPED:
            self.state = DockerState.PULLING
            self._runner = Thread(target=self._task_start)
            self._runner.start()

    def stop(self) -> None:
        if self.state == DockerState.STARTED:
            self.state = DockerState.STOPPING
            self._runner = Thread(target=self._task_stop)
            self._runner.start()

    @property
    def images(self) -> list[docker.models.images.Image]:
        if self.state == DockerState.NOT_AVAILABLE:
            return []
        return self.client.images.list()

    def compose_do(self, *commands: list[str]) -> subprocess.Popen:
        cmd = ["docker", "compose"]
        for composer_file in self.recipe.compose:
            cmd.extend(["-f", composer_file])
        cmd.extend(commands)
        _LOGGER.debug(f"Running command: {cmd}")

        return subprocess.Popen(
            cmd,
            cwd=self.settings.hive_repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=os.environ | self.recipe.environment,
        )
