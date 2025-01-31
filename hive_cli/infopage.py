import os
import signal

from fastapi import FastAPI
from nicegui import ui
from nicegui.events import ClickEventArguments

from hive_cli.styling import ICO

INST_LINK = (
    "https://github.com/caretech-owl/hive-cli/blob/main/images/create_cert.gif?raw=true"
)


class InfoPage:

    def __init__(self, fingerprint: str, app: FastAPI):
        self.fingerprint = fingerprint
        self.app = app

    def setup_ui(self) -> None:

        with ui.column() as col:
            col.tailwind("w-full flex-nowrap justify-center items-center")
            with ui.card() as card:
                card.tailwind("w-1/2")
                ui.label("Hive CLI").tailwind("text-2xl font-bold")
                ui.label(
                    "Welcome to the Hive! This is the first time you are starting the Hive CLI."
                )
                ui.label(
                    "A self-signed SSL certificate has been generated. "
                    "This certificate is used to secure the connection. "
                    "However, you need to manually verify this certificate. "
                )
                ui.markdown(
                    f'Click <a href="{INST_LINK}" target="_blank">Instructions</a> to see how to do this.'
                )
                with ui.row():
                    ui.label("Fingerprint:").tailwind("font-bold")
                    ui.label(self.fingerprint or "No fingerprint found!").tailwind(
                        "font-mono bg-gray-100 p-1"
                    )
                ui.label("Please note this fingerprint for future reference.")
                ui.label(
                    "Click the button below to restart the Hive CLI with a secure HTTPS connection."
                )
                with ui.row():
                    ins = ui.button(
                        "Instructions",
                        on_click=lambda _: ui.navigate.to(
                            INST_LINK,
                            new_tab=True,
                        ),
                    )

                    def _on_restart(_: ClickEventArguments) -> None:
                        host = os.getenv("HIVE_HOST", "localhost")
                        port = int(os.getenv("HIVE_PORT", 12121))
                        ui.run_javascript(
                            f'window.setTimeout(() => window.location.href = "https://{host}:{port}", 3000);'
                        )
                        card.remove(btn)
                        ui.spinner(size="2em")
                        os.kill(os.getppid(), signal.SIGINT)

                    btn = ui.button(
                        "Restart",
                        on_click=_on_restart,
                    )
            ui.image("/images/hive_logo.png").tailwind("w-1/4")

        with ui.footer().classes("bg-gray-100"):
            ui.label("© 2025 CareTech OWL").tailwind("text-xs text-gray-500")
        ui.run_with(self.app, favicon=ICO, title="Hive Cli")
