import logging
import re
from logging.handlers import MemoryHandler
from pathlib import Path
from threading import Thread, Timer

import yaml

from hive_cli.data import (
    COMPOSE_FILE_PATTERN,
    ComposerFile,
    DockerState,
    HiveData,
    Recipe,
    RepoState,
)
from hive_cli.docker import DockerController
from hive_cli.frontend import Frontend
from hive_cli.repo import RepoController

_LOGGER = logging.getLogger(__name__)


class Controller:

    def __init__(self, ui: Frontend, hive: HiveData) -> None:
        self.ui = ui
        self.hive = hive
        self.docker = DockerController(hive)
        self.repo = RepoController(hive)
        self.update_timer = Timer(hive.settings.update_interval, self.update)
        self.log_timer = Timer(hive.settings.log_interval, self.update_logs)
        self.ui.events.save_recipe.connect(self._on_save_recipe)
        self.ui.events.save_compose.connect(self._on_save_compose)
        self.ui.events.update.connect(self.update)
        self.ui.events.create_recipe.connect(self._on_create_recipe)
        self.ui.events.change_num_log_container.connect(lambda _: self.update_logs())
        self.ui.events.change_num_log_cli.connect(lambda _: self.update_logs())
        self.ui.events.save_settings.connect(self._on_save_settings)
        self.ui.events.reset_repo.connect(self.repo.reset_repo)
        self.ui.events.stop_docker.connect(self.docker.stop)
        self.ui.events.start_docker.connect(self.docker.start)
        self.ui.events.initialize_repo.connect(self.repo.init_repo)
        self.ui.events.commit_changes.connect(self.repo.commit_changes)
        self.ui.events.update_recipe.connect(self.update_recipe)
        self.ui.events.update_client.connect(self.docker.update_cli)
        self.log_handler: MemoryHandler | None = next(
            (
                handler
                for handler in logging.getLogger("hive_cli").handlers
                if isinstance(handler, MemoryHandler)
            ),
            None,
        )
        self.load_recipe()

    def _on_create_recipe(self) -> None:
        _LOGGER.info("Creating recipe for %s", self.hive.settings.hive_id)
        if self.hive.repo_state == RepoState.UP_TO_DATE:
            recipe = Recipe(
                path=self.hive.settings.hive_repo / f"{self.hive.settings.hive_id}.yml"
            )
            recipe.save()
            self.set_recipe(recipe)
        else:
            self.ui.notify(
                "Cannot create recipe. Repo is not available or outdated!",
                type="negative",
            )

    def _on_save_recipe(self, config: str) -> None:
        try:
            recipe = Recipe.model_validate_json(config)
            for compose in recipe.compose:
                if re.match(COMPOSE_FILE_PATTERN, compose) is None:
                    msg = (
                        f"Invalid compose path {compose}. "
                        f"Path must match '{COMPOSE_FILE_PATTERN}'."
                    )
                    raise ValueError(msg)
            recipe.save()
            self.set_recipe(recipe)
            self.repo.update_state()
            self.ui.notify("Recipe updated", type="positive")
        except Exception as e:
            _LOGGER.error("Error parsing recipe: %s", e)
            self.ui.notify(str(e), type="negative")

    def _on_save_compose(self, config: str, path: Path) -> None:
        try:
            compose_file = ComposerFile.model_validate_json(config)
            compose_file.save(path)
            self.ui.repo_status.refresh()
            self.ui.notify("Compose file updated", type="positive")
        except Exception as e:
            _LOGGER.error("Error parsing compose: %s", e)
            self.ui.notify(str(e), type="negative")
        self.repo.update_state()

    def _on_save_settings(self) -> None:
        self.hive.settings.save()
        if self.hive.settings.update_interval != self.update_timer.interval:
            self.update_timer.cancel()
            self.update_timer = Timer(self.hive.settings.update_interval, self.update)
            self.update_timer.start()
        self.ui.notify("Settings updated", type="positive")

    def update_recipe(self) -> None:
        _LOGGER.info("Recipe was changed remotely. Updating...")

        def _update_recipe() -> None:
            self.hive.repo_state = RepoState.UPDATING
            self.repo.update_repo()
            self.hive.repo_state = RepoState.UPDATING
            self.load_recipe()

        Thread(target=_update_recipe).start()

    def update(self) -> None:
        _LOGGER.debug("Update triggered")
        self.update_timer.cancel()
        self.docker.check_cli_update()
        self.repo.update_state()
        if (
            self.hive.repo_state == RepoState.UPDATE_AVAILABLE
            and self.hive.settings.auto_update_recipe
        ):
            self.update_recipe()
        self.update_timer = Timer(self.hive.settings.update_interval, self.update)
        self.update_timer.start()

    def update_logs(self) -> None:
        _LOGGER.debug("Refresh logs")
        self.log_timer.cancel()
        container_logs = self.docker.get_container_logs(self.hive.container_logs_num)
        cli_logs = (
            [
                self.log_handler.format(record)
                for record in self.log_handler.buffer[-self.hive.client_logs_num :]
            ]
            if self.log_handler
            else []
        )
        self.hive.client_logs = cli_logs
        self.hive.container_logs = container_logs
        self.ui.log_status.refresh()
        self.log_timer = Timer(self.hive.settings.log_interval, self.update_logs)
        self.log_timer.start()

    def load_recipe(self) -> None:
        recipe_file = self.hive.settings.hive_repo / f"{self.hive.settings.hive_id}.yml"
        if recipe_file.exists():
            with recipe_file.open("r") as f:
                obj = yaml.safe_load(f)
                obj["path"] = recipe_file
                recipe = Recipe.model_validate(obj)
        else:
            _LOGGER.warning("File %s not found.", recipe_file.resolve())
            recipe = None
        self.set_recipe(recipe)

    def _defered_set_recipe(self, recipe: Recipe | None) -> None:
        self.hive.recipe = recipe
        self.repo.update_state()
        self.docker.start()

    def set_recipe(self, recipe: Recipe | None) -> None:
        if self.hive.docker_state == DockerState.STARTED:
            self.docker.stop(lambda: self._defered_set_recipe(recipe))
        else:
            self.hive.recipe = recipe
            self.repo.update_state()
            self.docker.update_container_states()

    def __enter__(self) -> None:
        self.update()
        self.update_logs()

    def __exit__(self, exc_type, exc_value, traceback) -> None:  # noqa: ANN001
        self.update_timer.cancel()
        self.log_timer.cancel()
