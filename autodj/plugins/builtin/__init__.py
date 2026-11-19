"""Built-in plugins for CamfrogAutoDJ.

Exposes the built-in plugin classes so they can be imported both as
``autodj.plugins.builtin`` (package) and as submodules
``autodj.plugins.builtin.stats`` / ``autodj.plugins.builtin.help``
(which is how :class:`~autodj.plugins.manager.PluginManager` loads them).
"""

from __future__ import annotations

from .help import HelpPlugin
from .stats import StatsPlugin

__all__ = ["StatsPlugin", "HelpPlugin", "BUILTIN_PLUGINS", "get_builtin_plugin"]

# Plugin registry for builtin plugins
BUILTIN_PLUGINS = {
    "stats": StatsPlugin,
    "help": HelpPlugin,
}


def get_builtin_plugin(name: str) -> type | None:
    """Get a builtin plugin class by name."""
    return BUILTIN_PLUGINS.get(name)

