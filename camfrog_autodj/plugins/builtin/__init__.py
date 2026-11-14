"""Built-in plugins for CamfrogAutoDJ.

Exposes the built-in plugin classes so they can be imported both as
``camfrog_autodj.plugins.builtin`` (package) and as submodules
``camfrog_autodj.plugins.builtin.stats`` / ``camfrog_autodj.plugins.builtin.help``
(which is how :class:`~camfrog_autodj.plugins.manager.PluginManager` loads them).
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
