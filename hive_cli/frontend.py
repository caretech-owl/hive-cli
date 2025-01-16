import logging
import logging.handlers
import os
import signal
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from fastapi import FastAPI
from nicegui import ui
from nicegui.elements.mixins.validation_element import ValidationElement
from nicegui.events import ValueChangeEventArguments
from psygnal import Signal

from hive_cli import __version__
from hive_cli.config import load_settings
from hive_cli.data import ClientState, ComposerFile, HiveData, RepoState
from hive_cli.docker import DockerState
from hive_cli.styling import (
    DEACTIVATED_STYLE,
    HEADER_STYLE,
    ICO,
    INFO_STYLE,
    LOG_STYLE,
    PENDING_STYLE,
    SERVICE_ACTIVE_STYLE,
    SIMPLE_STYLE,
    TEXT_INFO_STYLE,
    WARNING_STYLE,
    copy_button,
    list_files,
)

_LOGGER = logging.getLogger(__name__)


class FrontendEvent:
    initialize_repo = Signal()
    commit_changes = Signal()
    reset_repo = Signal()
    create_recipe = Signal()
    save_recipe = Signal(str)
    save_compose = Signal(str, Path)
    change_num_log_container = Signal(int)
    change_num_log_cli = Signal(int)
    update = Signal()
    update_client = Signal()
    update_recipe = Signal()
    save_settings = Signal()
    start_docker = Signal()
    stop_docker = Signal()


class ErrorChecker:
    def __init__(self, hive: HiveData, *elements: ValidationElement) -> None:
        self.elements = elements
        self.hive = hive

    @property
    def no_errors(self) -> bool:
        return (
            all(
                validation(element.value)
                for element in self.elements
                for validation in (
                    element.validation.values()  # type: ignore[union-attr]
                    if hasattr(element.validation, "values")
                    else [element.validation] if element.validation else []
                )
            )
            and self.hive.docker_state == DockerState.STOPPED
        )


class Frontend:

    def __init__(
        self,
        hive: HiveData,
        app: FastAPI | None = None,
    ) -> None:
        self.app = app
        self.hive = hive
        self.log_timer = ui.timer(30, self.log_status.refresh, active=False)
        self.log_num_entries_cli = 20
        self.log_num_entries_com = 20
        self._recipe_expanded = False
        self._repo_expanded = False
        self._settings_expanded = False
        self.events = FrontendEvent()
        self.hive.events.recipe.connect(lambda _: self.recipe_status.refresh())
        self.hive.events.container_states.connect(
            lambda _: self.container_status.refresh()
        )
        self.hive.events.docker_state.connect(lambda _: self._on_docker_state_change())
        self.hive.events.client_state.connect(lambda _: self._on_cli_state_change())
        self.hive.events.repo_state.connect(lambda _: self._on_repo_state_change())

    def notify(
        self,
        msg: str,
        type: Literal["positive", "negative", "warning", "info", "ongoing"] = "info",
    ) -> None:
        ui.notification(msg, type=type)

    @ui.refreshable
    def repo_status(self) -> None:
        if self.hive.repo_state == RepoState.NOT_FOUND:
            ui.label("Repository not initialized").tailwind(WARNING_STYLE)
            ui.button("Initialize").on_click(self.events.initialize_repo.emit)
            return

        ui.label("Konfiguration:").tailwind(SIMPLE_STYLE)
        if self.hive.repo_state in [
            RepoState.CHANGED_LOCALLY,
            RepoState.CHANGES_COMMITTED,
        ]:
            ui.label(
                "Local Edits"
                if self.hive.repo_state == RepoState.CHANGED_LOCALLY
                else "Edits Committed"
            ).tailwind(INFO_STYLE)
            ui.button("Reset", icon="restore").on_click(
                lambda _: self.events.reset_repo.emit()
            )
            if self.hive.repo_state == RepoState.CHANGED_LOCALLY:
                ui.button("Commit", icon="upgrade").on_click(
                    lambda _: self.events.commit_changes.emit()
                )
        elif self.hive.repo_state == RepoState.UPDATE_AVAILABLE:
            ui.label("Update Available").tailwind(PENDING_STYLE)
            if not self.hive.settings.auto_update_recipe:
                ui.button("Update", icon="refresh").on_click(
                    lambda _: self.events.update_recipe.emit()
                )
            ui.button("Check", icon="refresh").on_click(
                lambda _: self.events.update.emit()
            )
        elif self.hive.repo_state == RepoState.UPDATING:
            ui.label("Updating").tailwind(PENDING_STYLE)
        else:
            ui.label("Aktuell").tailwind(INFO_STYLE)
            ui.button("Check", icon="refresh").on_click(
                lambda _: self.events.update.emit()
            )

    @ui.refreshable
    def recipe_status(self) -> None:
        if self.hive.recipe:
            with ui.expansion(
                "Recipe",
                icon="receipt_long",
                value=self._recipe_expanded,
                on_value_change=lambda evt: setattr(
                    self, "_recipe_expanded", evt.value
                ),
            ).classes("w-full"):
                read_only = (
                    self.hive.docker_state != DockerState.STOPPED
                    or self.hive.repo_state == RepoState.CHANGES_COMMITTED
                )
                ui.label(
                    self.hive.recipe.path.name + " 🔒" if read_only else ""
                ).tailwind(HEADER_STYLE)
                if self.hive.docker_state != DockerState.STOPPED:
                    ui.label("Recipe is read-only when Docker is not stopped").tailwind(
                        TEXT_INFO_STYLE
                    )
                ui.json_editor(
                    {
                        "content": {
                            "json": self.hive.recipe.model_dump_json(
                                indent=2, exclude_none=True
                            )
                        },
                        "readOnly": read_only,
                    },
                    on_change=lambda evt: self.events.save_recipe.emit(
                        evt.content["json"]
                    ),
                ).tailwind("w-full")
                for path, compose in self.hive.recipe.composer_files().items():
                    if compose:
                        ui.label(path.name + " 🔒" if read_only else "").tailwind(
                            SIMPLE_STYLE
                        )
                        ui.json_editor(
                            {
                                "content": {
                                    "json": compose.model_dump_json(
                                        indent=2, exclude_none=True
                                    )
                                },
                                "readOnly": read_only,
                            },
                            on_change=(
                                lambda evt, path=path: self.events.save_compose.emit(
                                    evt.content["json"], path
                                )
                            ),
                        ).tailwind("w-full")
                    else:

                        def on_create_compose(path: Path) -> None:
                            _LOGGER.info("Creating compose for %s", path)
                            if not self.hive.recipe:
                                msg = "Expected recipe to be set."
                                raise AssertionError(msg)
                            compose = ComposerFile(services={})
                            compose.save(path)
                            self.hive.recipe.save()
                            self.repo_status.refresh()

                        with ui.row():
                            ui.label(f"{path.name} not found").tailwind(WARNING_STYLE)
                            ui.button("Create", icon="refresh").on_click(
                                partial(on_create_compose, path)
                            )
        else:
            with ui.row():
                ui.label(
                    f"⚠️ No recipe for {self.hive.settings.hive_id} found!"
                ).tailwind(WARNING_STYLE)
                ui.button("Create", icon="refresh").on_click(
                    lambda _: self.events.create_recipe.emit()
                )

    @ui.refreshable
    def available_endpoints(self) -> None:
        if self.hive.recipe and self.hive.recipe.endpoints:
            with ui.row():
                for endpoint in self.hive.recipe.endpoints:
                    button = ui.button(
                        endpoint.name,
                        on_click=partial(
                            ui.run_javascript,
                            f"window.open(`{endpoint.protocol}://${{window.location.hostname}}:{endpoint.port}`)",
                        ),
                        icon=endpoint.icon,
                    )
                    button.tailwind(SERVICE_ACTIVE_STYLE)
                    if self.hive.docker_state != DockerState.STARTED:
                        button.disable()

    @ui.refreshable
    def container_status(self) -> None:
        ui.label("Container List").tailwind(HEADER_STYLE)
        states = self.hive.container_states
        labels = ["State", "Name", "Image", "Status"]
        if states:
            with ui.scroll_area().classes("grow"), ui.grid(columns=len(labels)):
                for label in labels:
                    ui.label(label)
                for container in states:
                    ui.label("🟢" if container.state == "running" else "🟡")
                    ui.label(container.name)
                    ui.label(container.image)
                    ui.label(container.status)
        else:
            ui.label("No running container found").tailwind(TEXT_INFO_STYLE)

    def change_log_num_entries_cli(self, evt: ValueChangeEventArguments) -> None:
        self.log_num_entries_cli = evt.value
        self.log_status.refresh()

    def change_log_num_entries_com(self, evt: ValueChangeEventArguments) -> None:
        self.log_num_entries_com = evt.value
        self.log_status.refresh()

    @ui.refreshable
    def log_status(self) -> None:
        with ui.row().classes("flex items-center"):
            ui.label("Container Log").tailwind(HEADER_STYLE)
            ui.select(
                options=[10, 20, 50, 100, 200],
                value=self.log_num_entries_com,
                on_change=self.change_log_num_entries_com,
            )
            ui.label("Einträge").tailwind(HEADER_STYLE)
        if self.hive.container_logs:
            with (
                ui.scroll_area().classes("grow").style(LOG_STYLE) as scroll,
                ui.column().style("gap: 0px; line-break: anywhere;"),
            ):
                for container_log in self.hive.container_logs:
                    ui.label(container_log)
                scroll.scroll_to(percent=100)
        else:
            ui.label("No container logs found").tailwind(TEXT_INFO_STYLE)
        with ui.row().classes("flex items-center"):
            ui.label("Client Log").tailwind(HEADER_STYLE)
            ui.select(
                options=[10, 20, 50, 100, 200],
                value=self.hive.container_logs_num,
                on_change=lambda evt: self.events.change_num_log_container.emit(
                    evt.value
                ),
            )
            ui.label("Einträge").tailwind(HEADER_STYLE)
        with (
            ui.scroll_area().classes("grow").style(LOG_STYLE) as scroll,
            ui.column().style("gap: 0px; line-break: anywhere;"),
        ):
            for log in self.hive.client_logs:
                ui.label(log)
            scroll.scroll_to(percent=100)

    @ui.refreshable
    def docker_status(self) -> None:
        docker_label = ui.label(f"{self.hive.docker_state.name}")

        match self.hive.docker_state:
            case DockerState.NOT_AVAILABLE | DockerState.NOT_CONFIGURED:
                docker_label.tailwind(WARNING_STYLE)
            case DockerState.STOPPED:
                docker_label.tailwind(DEACTIVATED_STYLE)
            case DockerState.STARTED:
                docker_label.tailwind(INFO_STYLE)
            case _:
                docker_label.tailwind(PENDING_STYLE)

        if self.hive.docker_state == DockerState.NOT_AVAILABLE:
            ui.button("Retry", icon="refresh").on_click(self.docker_status.refresh)
        elif self.hive.docker_state == DockerState.NOT_CONFIGURED:
            pass
        elif self.hive.docker_state == DockerState.STOPPED:
            ui.button("Start", icon="rocket_launch").on_click(
                lambda _: self.events.start_docker.emit()
            )
        elif self.hive.docker_state == DockerState.STARTED:
            ui.button("Stop", icon="power_settings_new").on_click(
                lambda _: self.events.stop_docker.emit()
            )
        else:
            ui.spinner(size="lg")

    @ui.refreshable
    def repo_list(self) -> None:
        if self.hive.repo_state != RepoState.NOT_FOUND:
            with ui.expansion(
                "Repository",
                icon="folder",
                value=self._repo_expanded,
                on_value_change=lambda evt: setattr(self, "_repo_expanded", evt.value),
            ).classes("w-full"):
                for level, name in list_files(self.hive.settings.hive_repo)[1:]:
                    with ui.row():
                        for _ in range(level - 2):
                            ui.space()
                        if level > 1:
                            ui.label(">")
                        ui.label(name)

    @ui.refreshable
    def footer(self) -> None:
        label = ui.label(__version__)
        label.tailwind("text-gray-500 font-semibold")
        if self.hive.client_state == ClientState.UPDATE_AVAILABLE:
            icon = ui.icon("cloud_download", size="1.5rem")
            icon.tailwind("text-sky-500 font-semibold cursor-pointer")
            icon.on("click", self.events.update_client.emit)
        elif self.hive.client_state == ClientState.UPDATING:
            ui.spinner(size="sm")
        elif self.hive.client_state == ClientState.RESTART_REQUIRED:
            icon = ui.icon("restart_alt", size="1.5rem")
            icon.tailwind("""text-sky-500 font-semibold cursor-pointer""")
            icon.on("click", lambda: os.kill(os.getppid(), signal.SIGINT))

    @ui.refreshable
    def settings_form(self) -> None:
        with (
            ui.expansion(
                "Einstellungen",
                icon="settings",
                value=self._settings_expanded,
                on_value_change=lambda evt: setattr(
                    self, "_settings_expanded", evt.value
                ),
            ).classes("w-full"),
            ui.column().classes("flex items-stretch"),
        ):
            settings = self.hive.settings
            msg_val_alnum = "Only alphanumeric characters are allowed."
            msg_val_len = "Must be between 4 and 32 characters."
            inp_id = ui.input(
                label="Hive ID",
                value=settings.hive_id,
                validation={
                    msg_val_len: lambda value: 4 <= len(value) <= 32,
                    msg_val_alnum: lambda value: str(value).isalnum(),
                },
                on_change=lambda evt: setattr(
                    settings,
                    "hive_id",
                    evt.value,
                ),
            )

            ui.number(
                label="Update Interval",
                value=settings.update_interval,
                min=5,
                max=24 * 60 * 60,
                on_change=lambda evt: (
                    setattr(settings, "update_interval", round(evt.value))
                    if evt.value is not None
                    else None
                ),
            )
            ui.number(
                label="Log Interval",
                value=settings.log_interval,
                min=1,
                max=24 * 60 * 60,
                on_change=lambda evt: (
                    setattr(settings, "log_interval", round(evt.value))
                    if evt.value is not None
                    else None
                ),
            )
            ui.checkbox(
                text="Auto Update Recipe",
                value=settings.auto_update_recipe,
                on_change=lambda evt: setattr(
                    settings, "auto_update_recipe", evt.value
                ),
            )

            def _refresh() -> None:
                self.hive.settings = load_settings(reload=True)
                self.settings_form.refresh()

            with ui.row():
                ui.button(icon="restore").on_click(_refresh)
                ui.button("Save").on_click(
                    lambda _: self.events.save_settings.emit()
                ).bind_enabled_from(ErrorChecker(self.hive, inp_id), "no_errors")

    def _on_docker_state_change(self) -> None:
        self.docker_status.refresh()
        self.available_endpoints.refresh()
        self.container_status.refresh()
        self.recipe_status.refresh()
        self.settings_form.refresh()

    def _on_repo_state_change(self) -> None:
        self.repo_status.refresh()
        self.repo_list.refresh()
        self.recipe_status.refresh()

    def _on_cli_state_change(self) -> None:
        self.footer.refresh()

    def register_github(self, url: str, token: str) -> ui.dialog:
        with ui.dialog() as dialog, ui.card():
            ui.label("Retrieve GitHub Token").tailwind(HEADER_STYLE)
            ui.label("To commit changes to the repository, a GitHub token is required.")
            with ui.row():
                ui.label(f"Pleaser enter")
                ui.label(token).style("font-weight: bold")
                copy_button(token, "Code")
                ui.label(f"to")
                ui.link(url, url, new_tab=True)
            with ui.row():
                ui.label("Status:")
                ui.spinner()
            ui.button("Cancel").on_click(dialog.close)
        return dialog

    def setup_ui(self) -> None:

        with (
            ui.row().classes("flex w-5/6 mx-auto space-x-4"),
            ui.column().classes("grow"),
        ):
            with ui.row().classes("w-full items-center"):
                ui.label("Docker: ").tailwind(SIMPLE_STYLE)

                # Docker Status
                self.docker_status()  # type: ignore[call-arg]

                # Repo
                self.repo_status()  # type: ignore[call-arg]

            ui.separator()
            # Endpoints
            self.available_endpoints()  # type: ignore[call-arg]
            ui.separator()

            # Container
            self.container_status()  # type: ignore[call-arg]

            # Log
            self.log_status()  # type: ignore[call-arg]
            self.log_timer.active = True

            # Recipe
            self.recipe_status()  # type: ignore[call-arg]

            # Repo List
            self.repo_list()  # type: ignore[call-arg]

            # Settings
            self.settings_form()  # type: ignore[call-arg]

        with ui.footer().classes("bg-gray-100"):
            ui.image("images/devcareop.svg").props("fit=scale-down").tailwind("w-10")
            ui.label().tailwind("grow")
            self.footer()  # type: ignore[call-arg]

        ui.page_title("CareDevOp Hive")

        if self.app:
            ui.run_with(self.app, favicon=ICO)
        else:
            ui.run(show=False, favicon=ICO)
