from functools import partial
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
WARNING_STYLE = (
    "bg-rose-500 text-white py-2 px-4 rounded-lg text-center text-lg font-bold"
)
INFO_STYLE = (
    "bg-green-500 text-white py-2 px-4 rounded-lg text-center text-lg font-bold"
)
SIMPLE_STYLE = "py-2 px-4 rounded-lg text-center text-lg font-bold"
LOG_STYLE = "font: 12px/1.5 monospace; white-space: pre-wrap; background-color: #f7f7f7; border-radius: 5px; border: 1px solid #ddd;"
SERVICE_ACTIVE_STYLE = (
    "bg-green-500 text-white py-2 px-4 rounded-lg text-center text-lg font-bold h-40"
)
DEACTIVATED_STYLE = (
    "bg-gray-500 text-white py-2 px-4 rounded-lg text-center text-lg font-bold"
)
PENDING_STYLE = (
    "bg-yellow-500 text-white py-2 px-4 rounded-lg text-center text-lg font-bold"
)
UPDATE_STYLE = (
    "bg-purple-500 text-white py-2 px-4 rounded-lg text-center text-lg font-bold"
)

_LOGGER = logging.getLogger(__name__)


class Frontend:

    def __init__(self, settings: Settings, docker: DockerController) -> None:
        self.settings = settings
        self.docker = docker
        self.hive = None
        self.timer: ui.timer = ui.timer(5, self.check_docker_state, active=False)
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
        ui.label("Konfiguration:").tailwind(SIMPLE_STYLE)
        if self.hive.local_version != self.hive.remote_version:

            def on_update_repo():
                update_repo()
                if self.docker.state == DockerState.STARTED:
                    self.stop_docker()
                self.repo_status.refresh()
                self.start_docker()

            ui.label("Update verfügbar").tailwind(INFO_STYLE)
            ui.button("Update", icon="upgrade").on_click(on_update_repo)
        else:
            ui.label("Aktuell").tailwind(SIMPLE_STYLE)
            ui.button("Check", icon="refresh").on_click(self.repo_status.refresh)

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
            ui.label(f"⚠️ No recipe for {self.settings.hive_id} found!").tailwind(
                WARNING_STYLE
            )

    @ui.refreshable
    def available_endpoints(self):
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
    def container_status(self):
        ui.label("Container List").tailwind(HEADER_STYLE)

        container_states = self.docker.get_container_states()
        labels = ["State", "Name", "Image", "Status"]
        if container_states:
            with ui.scroll_area().classes("grow"):
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

    def change_log_num_entries_cli(self, evt: ValueChangeEventArguments):
        self.log_num_entries_cli = evt.value
        self.log_status.refresh()

    def change_log_num_entries_com(self, evt: ValueChangeEventArguments):
        self.log_num_entries_com = evt.value
        self.log_status.refresh()

    @ui.refreshable
    def log_status(self):
        with ui.row().classes("flex items-center"):
            ui.label("Container Log").tailwind(HEADER_STYLE)
            ui.select(
                options=[10, 20, 50, 100, 200],
                value=self.log_num_entries_com,
                on_change=self.change_log_num_entries_com,
            )
            ui.label("Einträge").tailwind(HEADER_STYLE)
        with ui.scroll_area().classes("grow").style(LOG_STYLE):
            with ui.column().style("gap: 0px; line-break: anywhere;"):
                for record in self.docker.get_container_logs(self.log_num_entries_com):
                    ui.label(record)
        with ui.row().classes("flex items-center"):
            ui.label("Client Log").tailwind(HEADER_STYLE)
            ui.select(
                options=[10, 20, 50, 100, 200],
                value=self.log_num_entries_cli,
                on_change=self.change_log_num_entries_cli,
            )
            ui.label("Einträge").tailwind(HEADER_STYLE)
        if self.log_handler:
            with ui.scroll_area().classes("grow").style(LOG_STYLE):
                with ui.column().style("gap: 0.5rem; line-break: anywhere;"):
                    for record in self.log_handler.buffer[-self.log_num_entries_cli :][
                        ::-1
                    ]:
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
        self.docker_status.refresh()
        self.available_endpoints.refresh()
        self.timer.active = True

    def stop_docker(self):
        _LOGGER.info("Stopping Docker")
        self.docker.stop()
        self.docker_status.refresh()
        self.available_endpoints.refresh()
        self.timer.active = True

    @ui.refreshable
    def docker_status(self):
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
            ui.button("Start", icon="rocket_launch").on_click(self.start_docker)
        elif self.docker.state == DockerState.STARTED:
            ui.button("Stop", icon="power_settings_new").on_click(self.stop_docker)
        else:
            ui.spinner(size="lg")

    def setup_ui(self, app: FastAPI | None = None):

        with ui.row().classes("flex w-5/6 mx-auto space-x-4"):
            with ui.column().classes("grow"):
                with ui.row().classes("w-full items-center"):
                    ui.label("Docker: ").tailwind(SIMPLE_STYLE)

                    # Docker Status
                    self.docker_status()

                    # Repo
                    self.repo_status()

                ui.separator()
                # Endpoints
                self.available_endpoints()
                ui.separator()

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
                        ui.button("Save").on_click(
                            lambda: self.settings.save() or self.repo_status.refresh()
                        )

        with ui.footer().classes("bg-gray-100"):
            ui.image("images/devcareop.svg").props("fit=scale-down").tailwind("w-10")
            ui.label().tailwind("grow")
            ui.label(__version__).tailwind("text-gray-500 font-semibold")

        ui.page_title('CareDevOp Hive')
        # Define a custom favicon
        ICO = """
<svg width="100%" height="100%" viewBox="0 0 320 320" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" xml:space="preserve" xmlns:serif="http://www.serif.com/" style="fill-rule:evenodd;clip-rule:evenodd;stroke-linejoin:round;stroke-miterlimit:2;">
    <g transform="matrix(0.120848,0.120848,-0.120848,0.120848,85.2165,-21.2722)">
        <path d="M984.281,365.458L983.823,101.308C983.823,101.264 983.823,101.221 983.823,101.177C983.823,-128.021 1169.62,-313.823 1398.82,-313.823C1627.87,-313.823 1813.82,-127.867 1813.82,101.177C1813.82,330.376 1628.02,516.177 1398.82,516.177C1398.78,516.177 1398.74,516.177 1398.69,516.177L1134.54,515.719L1135,779.87C1135,779.913 1135,779.957 1135,780C1135,1009.2 949.198,1195 720,1195C490.955,1195 305,1009.05 305,780C305,550.802 490.802,365 720,365C720.043,365 720.087,365 720.13,365C720.13,365 843.054,365.213 984.281,365.458ZM984.541,515.459L719.947,515L719.903,515C573.592,515.052 455,633.677 455,780C455,926.257 573.743,1045 720,1045C866.338,1045 984.971,926.384 985,780.053L984.541,515.459ZM1134.28,365.718C1275.7,365.964 1398.9,366.177 1398.92,366.177C1545.23,366.125 1663.82,247.501 1663.82,101.177C1663.82,-45.08 1545.08,-163.823 1398.82,-163.823C1252.49,-163.823 1133.85,-45.207 1133.82,101.125L1134.28,365.718Z" style="fill:url(#_Linear1);"/>
    </g>
    <defs>
        <linearGradient id="_Linear1" x1="0" y1="0" x2="1" y2="0" gradientUnits="userSpaceOnUse" gradientTransform="matrix(1508.82,0,0,1508.82,305,440.589)"><stop offset="0" style="stop-color:rgb(19,170,202);stop-opacity:1"/><stop offset="0.5" style="stop-color:rgb(245,135,36);stop-opacity:1"/><stop offset="1" style="stop-color:rgb(251,196,15);stop-opacity:1"/></linearGradient>
    </defs>
</svg>
"""
        if app:
            ui.run_with(app, favicon=ICO)
        else:
            ui.run(show=False, favicon=ICO)
