from nicegui import ui

from hive_cli.config import load_settings
from hive_cli import __version__

def setup_ui(app):
    settings = load_settings()
    with ui.column():
        ui.label("Hello!")
        with ui.grid(columns="auto 1fr").classes('items-center'):
            ui.label("UUID:").style('text-align: right;')
            ui.label(settings.hive_uuid)

            ui.label("Update interval:").style('text-align: right;')
            ui.number(value=settings.update_interval,
                    min=10, max=44_640, step=10,
                    precision=0,
                    on_change=lambda e: print(f'Number changed to {e.value}'))

            ui.label("CLI Version:").style('text-align: right;')
            ui.label(__version__)

            ui.label("Recipe Version:").style('text-align: right;')
            ui.label(settings.version)

    ui.run_with(app)