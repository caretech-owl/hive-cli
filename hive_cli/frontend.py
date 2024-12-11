import logging
import logging.handlers
import os
import signal
from functools import partial
from logging.handlers import MemoryHandler
from typing import TYPE_CHECKING

from fastapi import FastAPI
from nicegui import app as ui_app
from nicegui import ui
from nicegui.events import ValueChangeEventArguments

from hive_cli import __version__
from hive_cli.config import Settings
from hive_cli.docker import DockerController, DockerState, UpdateState
from hive_cli.repo import get_data, init_repo, update_repo
from hive_cli.styling import (
    DEACTIVATED_STYLE,
    HEADER_STYLE,
    ICO,
    INFO_STYLE,
    LOG_STYLE,
    PENDING_STYLE,
    SERVICE_ACTIVE_STYLE,
    SIMPLE_STYLE,
    WARNING_STYLE,
)

if TYPE_CHECKING:
    from hive_cli.data import HiveData

_LOGGER = logging.getLogger(__name__)


class Frontend:

    def __init__(
        self, settings: Settings, docker: DockerController, app: FastAPI | None = None
    ) -> None:
        self.settings = settings
        self.docker = docker
        self._with_app = app is not None
        self.app = app or ui_app
        self.hive: HiveData | None = None
        self.log_timer = ui.timer(30, self.log_status.refresh, active=False)
        self.log_num_entries_cli = 20
        self.log_num_entries_com = 20
        self.log_handler: MemoryHandler | None = next(
            (
                handler
                for handler in logging.getLogger("hive_cli").handlers
                if isinstance(handler, MemoryHandler)
            ),
            None,
        )

    @ui.refreshable
    def repo_status(self) -> None:

        if not self.settings.hive_repo.exists():

            def on_init_repo() -> None:
                init_repo()
                self.repo_status.refresh()

            ui.label("Repository not initialized").tailwind(WARNING_STYLE)
            ui.button("Initialize").on_click(on_init_repo)
            return

        self.hive = get_data()
        if self.hive:
            self.docker.recipe = self.hive.recipe
            self.recipe_status.refresh()
            self.docker_status.refresh()
        ui.label("Konfiguration:").tailwind(SIMPLE_STYLE)
        if self.hive and self.hive.local_version != self.hive.remote_version:

            def on_update_repo() -> None:
                update_repo()
                if self.docker.state == DockerState.STARTED:
                    self.docker.stop()
                self.docker.start()

            ui.label("Update verfügbar").tailwind(INFO_STYLE)
            ui.button("Update", icon="upgrade").on_click(on_update_repo)
        else:
            ui.label("Aktuell").tailwind(SIMPLE_STYLE)
            ui.button("Check", icon="refresh").on_click(self.repo_status.refresh)

    @ui.refreshable
    def recipe_status(self) -> None:
        if self.hive and self.hive.recipe:
            with ui.expansion("Recipe", icon="receipt_long").classes("w-full"):
                ui.json_editor(
                    {
                        "content": {
                            "json": self.hive.recipe.model_dump_json(
                                indent=2, exclude_none=True
                            )
                        },
                        "readOnly": True,
                    }
                )
        else:
            ui.label(f"⚠️ No recipe for {self.settings.hive_id} found!").tailwind(
                WARNING_STYLE
            )

    @ui.refreshable
    def available_endpoints(self) -> None:
        if self.hive and self.hive.recipe and self.hive.recipe.endpoints:
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
                    if self.docker.state != DockerState.STARTED:
                        button.disable()

    @ui.refreshable
    def container_status(self) -> None:
        ui.label("Container List").tailwind(HEADER_STYLE)

        container_states = self.docker.get_container_states()
        labels = ["State", "Name", "Image", "Status"]
        if container_states:
            with ui.scroll_area().classes("grow"), ui.grid(columns=len(labels)):
                for label in labels:
                    ui.label(label)
                for container in container_states:
                    ui.label("🟢" if container.state == "running" else "🟡")
                    ui.label(container.name)
                    ui.label(container.image)
                    ui.label(container.status)
        else:
            ui.label("No running container found")

    def change_log_num_entries_cli(self, evt: ValueChangeEventArguments) -> None:
        self.log_num_entries_cli = evt.value
        self.log_status.refresh()

    def change_log_num_entries_com(self, evt: ValueChangeEventArguments) -> None:
        self.log_num_entries_com = evt.value
        self.log_status.refresh()

    @ui.refreshable
    def log_status(self) -> None:
        self.container_status.refresh()
        with ui.row().classes("flex items-center"):
            ui.label("Container Log").tailwind(HEADER_STYLE)
            ui.select(
                options=[10, 20, 50, 100, 200],
                value=self.log_num_entries_com,
                on_change=self.change_log_num_entries_com,
            )
            ui.label("Einträge").tailwind(HEADER_STYLE)
        with (
            ui.scroll_area().classes("grow").style(LOG_STYLE),
            ui.column().style("gap: 0px; line-break: anywhere;"),
        ):
            for container_log in self.docker.get_container_logs(
                self.log_num_entries_com
            ):
                ui.label(container_log)
        with ui.row().classes("flex items-center"):
            ui.label("Client Log").tailwind(HEADER_STYLE)
            ui.select(
                options=[10, 20, 50, 100, 200],
                value=self.log_num_entries_cli,
                on_change=self.change_log_num_entries_cli,
            )
            ui.label("Einträge").tailwind(HEADER_STYLE)
        if self.log_handler:
            with (
                ui.scroll_area().classes("grow").style(LOG_STYLE),
                ui.column().style("gap: 0.5rem; line-break: anywhere;"),
            ):
                for record in self.log_handler.buffer[-self.log_num_entries_cli :][
                    ::-1
                ]:
                    ui.label(self.log_handler.format(record))

    @ui.refreshable
    def docker_status(self) -> None:
        docker_label = ui.label(f"{self.docker.state.name}")

        match self.docker.state:
            case DockerState.NOT_AVAILABLE | DockerState.NOT_CONFIGURED:
                docker_label.tailwind(WARNING_STYLE)
            case DockerState.STOPPED:
                docker_label.tailwind(DEACTIVATED_STYLE)
            case DockerState.STARTED:
                docker_label.tailwind(INFO_STYLE)
            case _:
                docker_label.tailwind(PENDING_STYLE)

        if self.docker.state == DockerState.NOT_AVAILABLE:
            ui.button("Retry", icon="refresh").on_click(self.docker_status.refresh)
        elif self.docker.state == DockerState.NOT_CONFIGURED:
            pass
        elif self.docker.state == DockerState.STOPPED:
            ui.button("Start", icon="rocket_launch").on_click(self.docker.start)
        elif self.docker.state == DockerState.STARTED:
            ui.button("Stop", icon="power_settings_new").on_click(self.docker.stop)
        else:
            ui.spinner(size="lg")

    @ui.refreshable
    def footer(self) -> None:
        label = ui.label(__version__)
        label.tailwind("text-gray-500 font-semibold")
        if self.docker.cli_state == UpdateState.UPDATE_AVAILABLE:
            icon = ui.icon("cloud_download", size="1.5rem")
            icon.tailwind("text-sky-500 font-semibold cursor-pointer")
            icon.on("click", self.docker.update_cli)
        elif self.docker.cli_state == UpdateState.UPDATING:
            ui.spinner(size="sm")
        elif self.docker.cli_state == UpdateState.RESTART_REQUIRED:
            icon = ui.icon("restart_alt", size="1.5rem")
            icon.tailwind("""text-sky-500 font-semibold cursor-pointer""")
            icon.on("click", lambda: os.kill(os.getppid(), signal.SIGINT))

    def _on_docker_state_change(self) -> None:
        self.docker_status.refresh()
        self.available_endpoints.refresh()
        self.container_status.refresh()

    def _on_cli_state_change(self) -> None:
        self.footer.refresh()

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

            if not self.docker.images:
                ui.label("No images found")
            else:
                with ui.expansion("Images", icon="image").classes("w-full"):
                    for img in self.docker.images:
                        if img.tags:
                            ui.label(img.tags[0])

            with (
                ui.expansion("Einstellungen", icon="settings").classes("w-full"),
                ui.row().classes("w-full flex items-center"),
            ):
                settings = self.settings
                ui.input(
                    label="Hive ID",
                    value=str(self.settings.hive_id),
                    validation={
                        "Input must be a number!": lambda value: value.isdigit()
                    },
                    on_change=lambda evt: setattr(
                        settings,
                        "hive_id",
                        int(evt.value) if evt.value.isdigit() else evt.value,
                    ),
                )

                def on_save() -> None:
                    self.settings.save()
                    self.repo_status.refresh()

                ui.button("Save").on_click(on_save)

        with ui.footer().classes("bg-gray-100"):
            ui.image("images/devcareop.svg").props("fit=scale-down").tailwind("w-10")
            ui.label().tailwind("grow")
            self.footer()  # type: ignore[call-arg]

        ui.page_title("CareDevOp Hive")

        # Register listeners
        self.docker.state_listener.append(self._on_docker_state_change)
        self.docker.cli_state_listener.append(self._on_cli_state_change)

        if self._with_app:
            ui.run_with(self.app, favicon=ICO)
        else:
            ui.run(show=False, favicon=ICO)
