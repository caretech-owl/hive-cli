import logging.handlers
from fastapi import FastAPI
from nicegui import ui
from nicegui.events import ValueChangeEventArguments
import logging
from logging.handlers import MemoryHandler
from hive_cli.config import Settings
from hive_cli import __version__
from hive_cli.docker import DockerController, DockerState
from hive_cli.repo import get_data, init_repo, update_repo

HEADER_STYLE = "text-lg"
SUBSECTION_STYLE = "font-bold"
WARNING_STYLE = (
    "bg-rose-500 text-white py-2 px-4 rounded-lg text-center text-lg font-bold"
)
INFO_STYLE = (
    "bg-green-500 text-white py-2 px-4 rounded-lg text-center text-lg font-bold"
)
SIMPLE_STYLE = "py-2 px-4 rounded-lg text-center text-lg font-bold"
LOG_STYLE = "font: 12px/1.5 monospace; white-space: pre-wrap; background-color: #f7f7f7; border-radius: 5px; border: 1px solid #ddd;"
SERVICE_ACTIVE_STYLE = "bg-green-500 text-white py-2 px-4 rounded-lg text-center text-lg font-bold"
SERVICE_INACTIVE_STYLE = "bg-gray-500 text-white py-2 px-4 rounded-lg text-center text-lg font-bold"


_LOGGER = logging.getLogger(__name__)


class Frontend:

    def __init__(self, settings: Settings, docker: DockerController) -> None:
        self.settings = settings
        self.docker = docker
        self.hive = None
        self.timer: ui.timer = ui.timer(5, self.check_docker_state, active=False)
        self.log_timer = ui.timer(30, self.log_status.refresh, active=False)
        self.num_entries = 20
        self.log_handler: MemoryHandler | None = next(
            (
                handler
                for handler in logging.getLogger("hive_cli").handlers
                if isinstance(handler, MemoryHandler)
            ),
            None,
        )

    @ui.refreshable
    def repo_status(self):

        if not self.settings.hive_repo.exists():

            def on_init_repo():
                init_repo()
                self.repo_status.refresh()

            ui.label("Repository not initialized").tailwind(WARNING_STYLE)
            ui.button("Initialize").on_click(on_init_repo)
            return

        self.hive = get_data()
        self.docker.recipe = self.hive.recipe
        self.recipe_status.refresh()
        self.docker_status.refresh()
        if self.hive.local_version != self.hive.remote_version:

            def on_update_repo():
                update_repo()
                if self.docker.state == DockerState.STARTED:
                    self.stop_docker()
                self.repo_status.refresh()
                self.start_docker()

            ui.label("Konfiguration: Update verfügbar").tailwind(INFO_STYLE)
            ui.button("Update").on_click(on_update_repo)
        else:
            ui.label("Konfiguration: Aktuell").tailwind(INFO_STYLE)
            ui.button("Check").on_click(self.repo_status.refresh)

    @ui.refreshable
    def recipe_status(self):
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
            ui.label(
                f"⚠️ No recipe for {self.settings.hive_id} found!"
            ).tailwind(WARNING_STYLE)

    @ui.refreshable
    def available_endpoints(self):
        if self.hive and self.hive.recipe:
            for endpoint in self.hive.recipe.endpoints:
                ui.link(
                    endpoint.name, f"{endpoint.protocol}://localhost:{endpoint.port}"
                ).tailwind(SERVICE_ACTIVE_STYLE) if self.docker.state == DockerState.STARTED else ui.label(
                    endpoint.name
                ).tailwind(SERVICE_INACTIVE_STYLE)

    @ui.refreshable
    def container_status(self):
        ui.label("Container List").tailwind(HEADER_STYLE)

        container_states = self.docker.get_container_states()
        labels = ["State", "Name", "Image", "Status"]
        if container_states:
            with ui.scroll_area():
                with ui.grid(columns=len(labels)):
                    for label in labels:
                        ui.label(label)
                    for container in container_states:
                        ui.label("🟢" if container.state == "running" else "🟡")
                        ui.label(container.name)
                        ui.label(container.image)
                        ui.label(container.status)
        else:
            ui.label("No running container found")

    def change_log_num_entries(self, evt: ValueChangeEventArguments):
        self.num_entries = evt.value
        self.log_status.refresh()

    @ui.refreshable
    def log_status(self):
        with ui.row().classes("flex items-center"):
            ui.label("Log").tailwind(HEADER_STYLE)
            ui.select(
                options=[10, 20, 50, 100, 200],
                value=self.num_entries,
                on_change=self.change_log_num_entries,
            )
            ui.label("Einträge").tailwind(HEADER_STYLE)
        if self.log_handler:
            with ui.scroll_area().classes("grow").style(LOG_STYLE):
                for record in self.log_handler.buffer[-self.num_entries :][::-1]:
                    ui.label(self.log_handler.format(record))

    def check_docker_state(self):
        _LOGGER.debug("Checking Docker state %s", self.docker.state.name)
        if self.docker.state in [DockerState.STARTED, DockerState.STOPPED]:
            _LOGGER.debug("Cancelling timer")
            self.timer.active = False
            self.available_endpoints.refresh()
        self.container_status.refresh()
        self.docker_status.refresh()

    def start_docker(self):
        _LOGGER.info("Starting Docker")
        self.docker.start()
        self.timer.active = True

    def stop_docker(self):
        _LOGGER.info("Stopping Docker")
        self.docker.stop()
        self.timer.active = True

    @ui.refreshable
    def docker_status(self):
        ui.label(f"Docker: {self.docker.state.name}").tailwind(
            INFO_STYLE
            if self.docker.state != DockerState.NOT_AVAILABLE
            else WARNING_STYLE
        )
        if self.docker.state == DockerState.NOT_AVAILABLE:
            ui.button("Retry").on_click(self.docker_status.refresh)
        elif self.docker.state == DockerState.NOT_CONFIGURED:
            pass
        elif self.docker.state == DockerState.STOPPED:
            ui.button("Start").on_click(self.start_docker)
        elif self.docker.state == DockerState.STARTED:
            ui.button("Stop").on_click(self.stop_docker)
        else:
            ui.spinner(size="lg")

    def setup_ui(self, app: FastAPI | None = None):
        with (
            ui.header(elevated=True)
            .style("background-color: #3874c8")
            .classes("items-center justify-between")
        ):
            ui.label("CareDevOps")
        with ui.row().classes("flex w-5/6 mx-auto space-x-4"):
            with ui.column().classes("grow"):
                with ui.row().classes("w-full items-center"):
                    ui.label("Status").tailwind(SIMPLE_STYLE)

                    # Docker Status
                    self.docker_status()

                    # Repo
                    self.repo_status()
                
                self.available_endpoints()

                # Container
                self.container_status()

                # Log
                self.log_status()
                self.log_timer.active = True

                # Recipe
                self.recipe_status()

                if not self.docker.images:
                    ui.label("No images found")
                else:
                    with ui.expansion("Images", icon="image").classes("w-full"):
                        for img in self.docker.images:
                            if img.tags:
                                ui.label(img.tags[0])

                with ui.expansion("Einstellungen", icon="settings").classes("w-full"):
                    with ui.row().classes("w-full flex items-center"):
                        settings = self.settings
                        ui.input(
                            label="Hive ID",
                            value=self.settings.hive_id,
                            validation={
                                "Input must be a number!": lambda value: value.isdigit()
                            },
                            on_change=lambda evt: setattr(
                                settings,
                                "hive_id",
                                int(evt.value) if evt.value.isdigit() else evt.value,
                            ),
                        )
                        ui.button("Save").on_click(lambda: self.settings.save() or self.repo_status.refresh())

        with ui.footer():
            ui.label("CLI Version:")
            ui.label(__version__)

        if app:
            ui.run_with(app)
        else:
            ui.run(show=False)
