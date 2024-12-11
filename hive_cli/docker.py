import enum
import logging
import os
import subprocess
from pathlib import Path
from threading import Thread
from typing import Callable

import docker
import docker.models
import docker.models.images
from pydantic import BaseModel, Field

from hive_cli import __version__
from hive_cli.config import Settings
from hive_cli.data import Recipe

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


class UpdateState(enum.Enum):
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


class DockerController:

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._state = DockerState.NOT_CONFIGURED
        self.state_listener: list[Callable] = []
        self.client = None
        self._cli_state = UpdateState.UP_TO_DATE
        self.cli_state_listener: list[Callable] = []
        self._runner = None
        self._recipe: Recipe | None = None
        try:
            self.client = docker.from_env()
        except Exception as e:
            _LOGGER.error(e)
            self.state = DockerState.NOT_AVAILABLE

    @property
    def state(self) -> DockerState:
        return self._state

    @state.setter
    def state(self, value: DockerState) -> None:
        if value != self._state:
            _LOGGER.info("State changed from %s to %s", self._state, value)
            self._state = value
            for listener in self.state_listener:
                listener()

    @property
    def cli_state(self) -> UpdateState:
        return self._cli_state

    @cli_state.setter
    def cli_state(self, value: UpdateState) -> None:
        if value != self._cli_state:
            _LOGGER.info("CLI state changed from %s to %s", self._cli_state, value)
            self._cli_state = value
            for listener in self.cli_state_listener:
                listener()

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
            path = (
                Path(composer_file)
                if composer_file.startswith("/")
                else self.recipe.path.parent / composer_file
            ).resolve()
            if path.exists():
                cmd.extend(["-f", composer_file])
        if len(cmd) == 2:
            _LOGGER.error("No valid composer files found.")
            return []
        cmd.extend(["ps", "--format", "json"])
        _LOGGER.debug("Running command: %s", " ".join(cmd))
        res = subprocess.check_output(
            cmd, cwd=self.recipe.path.parent, env=os.environ | self.recipe.environment
        ).decode("utf-8")
        return [ContainerState.model_validate_json(line) for line in res.splitlines()]

    def get_container_logs(self, num_entries: int) -> list[str]:
        if self.recipe is None:
            return []

        pipe = self.compose_do("logs", "--no-color", "-n", str(num_entries))
        if pipe is not None and pipe.stdout is not None:
            return [line.decode("utf-8").strip() for line in pipe.stdout]
        return []

    def _task_update(self) -> None:
        if self.recipe is not None:
            cmd = ["docker", "pull", "ghcr.io/caretech-owl/hive-cli:latest"]
            _LOGGER.debug("Running command: %s", " ".join(cmd))
            subprocess.run(cmd, env=os.environ | self.recipe.environment)
            with (self.settings.hive_repo.parent / "_restart").open("w+"):
                pass
            _LOGGER.info("hive-cli update complete")
            self.cli_state = UpdateState.RESTART_REQUIRED

    def update_cli(self) -> None:
        self.cli_state = UpdateState.UPDATING
        thread = Thread(target=self._task_update)
        thread.start()

    def _task_start(self) -> None:
        if self.recipe is None:
            return
        for composer_file in self.recipe.composer_files().values():
            for image_name in composer_file.images:
                _LOGGER.info("Pulling image: %s", image_name)
                pipe = self.compose_do("pull", image_name)
                if pipe is not None and pipe.stdout is not None:
                    for line in pipe.stdout:
                        _LOGGER.debug(line.decode("utf-8").strip())
                else:
                    _LOGGER.warning("Received no output from Docker Compose")
        _LOGGER.info("Starting Docker Compose")
        self.state = DockerState.STARTING
        pipe = self.compose_do("up", "-d")
        if pipe is not None and pipe.stdout is not None:
            for line in pipe.stdout:
                _LOGGER.debug(line.decode("utf-8").strip())
        else:
            _LOGGER.warning("Received no output from Docker Compose")
        self.state = DockerState.STARTED

    def _task_stop(self) -> None:
        _LOGGER.info("Stopping Docker Compose")
        pipe = self.compose_do("down")
        if pipe is not None and pipe.stdout is not None:
            for line in pipe.stdout:
                _LOGGER.debug(line.decode("utf-8").strip())
        else:
            _LOGGER.warning("Received no output from Docker Compose")
        self.state = DockerState.STOPPED

    def _task_manifest(self) -> None:
        _LOGGER.info("Checking for hive-cli updates")
        cmd = ["docker", "manifest", "inspect"]
        try:
            local = subprocess.check_output(
                cmd + [f"ghcr.io/caretech-owl/hive-cli:{__version__}"],
                env=os.environ | self.recipe.environment if self.recipe else os.environ,
            )
        except Exception as e:
            _LOGGER.warning(e)
            local = None
        try:
            remote = subprocess.check_output(
                cmd + ["ghcr.io/caretech-owl/hive-cli:latest"],
                env=os.environ | self.recipe.environment if self.recipe else os.environ,
            )
            if local != remote:
                _LOGGER.info("hive-cli update available")
                self.cli_state = UpdateState.UPDATE_AVAILABLE
            else:
                _LOGGER.info("hive-cli is up to date")
        except Exception as e:
            _LOGGER.warning(e)

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

    def check_cli_update(self) -> None:
        self._runner = Thread(target=self._task_manifest)
        self._runner.start()

    @property
    def images(self) -> list[docker.models.images.Image]:
        if self.state == DockerState.NOT_AVAILABLE or self.client is None:
            return []
        return self.client.images.list()

    def compose_do(self, *commands: str) -> subprocess.Popen | None:
        if self.recipe is None:
            _LOGGER.error("No recipe set.")
            return None
        cmd = ["docker", "compose"]
        for composer_file in self.recipe.compose:
            cmd.extend(["-f", composer_file])
        cmd.extend(commands)
        _LOGGER.debug("Running command: %s", " ".join(cmd))

        return subprocess.Popen(
            cmd,
            cwd=self.settings.hive_repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=os.environ | self.recipe.environment,
        )
