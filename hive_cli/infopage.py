import os
import signal

from fastapi import FastAPI
from nicegui import ui

from hive_cli.styling import HEADER_STYLE, ICO


class InfoPage:

    def __init__(self, fingerprint: str, app: FastAPI):
        self.fingerprint = fingerprint
        self.app = app

    def setup_ui(self) -> None:
        host = os.getenv("HIVE_HOST", "localhost")
        port = int(os.getenv("HIVE_PORT", 12121))

        def _on_restart(_) -> None:
            ui.run_javascript(
                f'window.setTimeout(() => window.location.href = "https://{host}:{port}", 3000);'
            )
            os.kill(os.getppid(), signal.SIGINT)

        with ui.column() as c:
            ui.label("Hive CLI").tailwind(HEADER_STYLE)
            ui.label(
                "Welcome to the Hive. This is the first time you are starting the Hive CLI."
            )
            ui.label(
                "A self-signed SSL certificate has been generated. "
                "This certificate is used to secure the connection. "
                "However, you need to manually verify this certificate. "
            )
            ui.markdown("Click **Instructions** to see how to do this.")
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
                        "https://github.com/caretech-owl/hive-cli/blob/main/images/create_cert.gif?raw=true",
                        new_tab=True,
                    ),
                )
                btn = ui.button(
                    "Restart",
                    on_click=_on_restart,
                )
                btn.on_click(lambda _: c.remove(btn) or ui.spinner(size="2em"))
        ui.run_with(self.app, favicon=ICO, title="Hive Cli")
