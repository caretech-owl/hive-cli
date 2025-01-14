import logging
import os
import subprocess
from pathlib import Path
from threading import Thread
from typing import Callable

import docker
import docker.models
import docker.models.images

from hive_cli import __version__
from hive_cli.data import ClientState, ContainerState, DockerState, HiveData

_LOGGER = logging.getLogger(__name__)


class DockerController:

    def __init__(self, hive: HiveData) -> None:
        self.hive = hive
        self.client = None
        self._runner: Thread | None = None
        try:
            self.client = docker.from_env()
            self.update_container_states()
        except Exception as e:
            _LOGGER.error(e)
            self.hive.docker_state = DockerState.NOT_AVAILABLE

    def get_container_states(self) -> list[ContainerState]:
        recipe = self.hive.recipe
        if recipe is None:
            return []

        cmd = ["docker", "compose"]
        for composer_file in recipe.compose:
            path = (
                Path(composer_file)
                if composer_file.startswith("/")
                else recipe.path.parent / composer_file
            ).resolve()
            if path.exists():
                cmd.extend(["-f", composer_file])
        if len(cmd) == 2:
            _LOGGER.error("No valid composer files found.")
            return []
        cmd.extend(["ps", "--format", "json"])
        _LOGGER.debug("Running command: %s", " ".join(cmd))
        try:
            res = subprocess.check_output(
                cmd,
                cwd=recipe.path.parent,
                env=os.environ | recipe.environment,
            ).decode("utf-8")
            return [
                ContainerState.model_validate_json(line) for line in res.splitlines()
            ]
        except Exception as e:
            _LOGGER.error(e)
            self.hive.docker_state = DockerState.UNKNOWN
            return []

    def get_container_logs(self, num_entries: int) -> list[str]:
        if self.hive.recipe is None:
            return []

        pipe = self.compose_do("logs", "--no-color", "-n", str(num_entries))
        if pipe is not None and pipe.stdout is not None:
            return [line.decode("utf-8").strip() for line in pipe.stdout]
        return []

    def _task_update(self) -> None:
        if self.hive.recipe is not None:
            cmd = ["docker", "pull", "ghcr.io/caretech-owl/hive-cli:latest"]
            _LOGGER.debug("Running command: %s", " ".join(cmd))
            subprocess.run(cmd, env=os.environ | self.hive.recipe.environment)
            with (self.hive.settings.hive_repo.parent / "_restart").open("w+"):
                pass
            _LOGGER.info("hive-cli update complete")
            self.hive.client_state = ClientState.RESTART_REQUIRED

    def update_cli(self) -> None:
        self.hive.client_state = ClientState.UPDATING
        thread = Thread(target=self._task_update)
        thread.start()

    def _task_start(self) -> None:
        recipe = self.hive.recipe
        if recipe is None:
            return
        for composer_file in recipe.composer_files().values():
            if composer_file is None:
                continue
            for image_name in composer_file.images:
                _LOGGER.info("Pulling image: %s", image_name)
                pipe = self.compose_do("pull", image_name)
                if pipe is not None and pipe.stdout is not None:
                    for line in pipe.stdout:
                        _LOGGER.debug(line.decode("utf-8").strip())
                else:
                    _LOGGER.warning("Received no output from Docker Compose")
        _LOGGER.info("Starting Docker Compose")
        self.hive.docker_state = DockerState.STARTING
        pipe = self.compose_do("up", "-d")
        if pipe is not None and pipe.stdout is not None:
            for line in pipe.stdout:
                _LOGGER.debug(line.decode("utf-8").strip())
        else:
            _LOGGER.warning("Received no output from Docker Compose")
        self.update_container_states()

    def _task_stop(self, cb: Callable | None) -> None:
        _LOGGER.info("Stopping Docker Compose")
        pipe = self.compose_do("down")
        if pipe is not None and pipe.stdout is not None:
            for line in pipe.stdout:
                _LOGGER.debug(line.decode("utf-8").strip())
        else:
            _LOGGER.warning("Received no output from Docker Compose")
        self.update_container_states()
        if cb is not None:
            cb()

    def _task_manifest(self) -> None:
        _LOGGER.info("Checking for hive-cli updates")
        cmd = ["docker", "manifest", "inspect"]
        recipe = self.hive.recipe
        try:
            local = subprocess.check_output(
                cmd + [f"ghcr.io/caretech-owl/hive-cli:{__version__}"],
                env=os.environ | recipe.environment if recipe else os.environ,
            )
        except Exception as e:
            _LOGGER.warning(e)
            local = None
        try:
            remote = subprocess.check_output(
                cmd + ["ghcr.io/caretech-owl/hive-cli:latest"],
                env=os.environ | recipe.environment if recipe else os.environ,
            )
            if local != remote:
                _LOGGER.info("hive-cli update available")
                self.hive.client_state = ClientState.UPDATE_AVAILABLE
            else:
                _LOGGER.info("hive-cli is up to date")
        except Exception as e:
            _LOGGER.warning(e)

    def start(self) -> None:
        if self.hive.docker_state == DockerState.STOPPED:
            _LOGGER.info("Starting Docker")
            self.hive.docker_state = DockerState.PULLING
            self._runner = Thread(target=self._task_start)
            self._runner.start()

    def stop(self, cb: Callable | None = None) -> None:
        if self.hive.docker_state == DockerState.STARTED:
            self.hive.docker_state = DockerState.STOPPING
            self._runner = Thread(target=self._task_stop, args=(cb,))
            self._runner.start()

    def update_container_states(self) -> None:
        self.hive.container_states = self.get_container_states()
        self.hive.docker_state = (
            DockerState.STARTED if self.hive.container_states else DockerState.STOPPED
        )

    def check_cli_update(self) -> None:
        self._runner = Thread(target=self._task_manifest)
        self._runner.start()

    @property
    def images(self) -> list[docker.models.images.Image]:
        if self.hive.docker_state == DockerState.NOT_AVAILABLE or self.client is None:
            return []
        return self.client.images.list()

    def compose_do(self, *commands: str) -> subprocess.Popen | None:
        if self.hive.recipe is None:
            _LOGGER.error("No recipe set.")
            return None
        cmd = ["docker", "compose"]
        for composer_file in self.hive.recipe.compose:
            cmd.extend(["-f", composer_file])
        cmd.extend(commands)
        _LOGGER.debug("Running command: %s", " ".join(cmd))

        return subprocess.Popen(
            cmd,
            cwd=self.hive.settings.hive_repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=os.environ | self.hive.recipe.environment,
        )
