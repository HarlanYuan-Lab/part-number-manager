"""Part Number Manager - application package.

Layered architecture:
    config         -> constants / paths
    models         -> data models
    repositories   -> SQLite data access
    services       -> business logic
    exporter       -> Excel export
    ui             -> presentation (theme / panels / dialogs / window)
"""

from .config import APP_NAME, APP_VERSION

__all__ = ["APP_NAME", "APP_VERSION"]
__version__ = APP_VERSION
