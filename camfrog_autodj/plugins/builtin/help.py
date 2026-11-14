"""Built-in help plugin: provides extended help information."""

from __future__ import annotations

import logging

from ..base import Plugin

log = logging.getLogger("autodj.plugins.help")


class HelpPlugin(Plugin):
    """Provides extended help information."""

    name = "help"
    version = "1.0.0"
    description = "Extended help command with plugin information"

    def __init__(self):
        super().__init__()

    def on_load(self, interface) -> None:
        super().on_load(interface)
        log.info("Help plugin loaded")

    def on_command(self, command: str, user: str, args: str, is_admin: bool) -> bool:
        if command.lower() in ("help", "plugins", "ช่วยเหลือ"):
            plugins = self.interface.list_plugins()
            if plugins:
                plugin_list = ", ".join(f"{p['name']} v{p['version']}" for p in plugins)
                msg = f"📦 Loaded plugins: {plugin_list}"
            else:
                msg = "📦 No plugins loaded"
            self.interface.say(msg)
            return True
        return False
