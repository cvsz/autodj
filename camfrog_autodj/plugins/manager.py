"""Plugin manager for CamfrogAutoDJ."""

from __future__ import annotations

import importlib
import logging
from typing import TYPE_CHECKING, Any

from .base import Plugin, PluginInterface

if TYPE_CHECKING:
    from camfrog_autodj.engine import Engine

log = logging.getLogger("autodj.plugins")


class PluginManager:
    """Manages plugin lifecycle and event distribution."""
    
    def __init__(self, engine: "Engine", plugin_names: list[str]):
        self.engine = engine
        self.plugin_names = plugin_names
        self.plugins: dict[str, Plugin] = {}
        self._interface = PluginInterface(engine)
    
    def load_plugins(self) -> None:
        """Load all configured plugins."""
        for name in self.plugin_names:
            try:
                self.load_plugin(name)
            except Exception:
                log.exception("Failed to load plugin %s", name)
    
    def load_plugin(self, name: str) -> None:
        """Load a single plugin by name."""
        if name in self.plugins:
            log.warning("Plugin %s already loaded", name)
            return
        
        try:
            if name.startswith("builtin."):
                mod = importlib.import_module(f"camfrog_autodj.plugins.builtin.{name[8:]}")
            else:
                mod = importlib.import_module(name)
            
            # Find Plugin subclass
            for attr_name in dir(mod):
                obj = getattr(mod, attr_name)
                if isinstance(obj, type) and issubclass(obj, Plugin) and obj is not Plugin:
                    plugin = obj()
                    plugin.on_load(self._interface)
                    plugin_name = plugin.name or name
                    self.plugins[plugin_name] = plugin
                    log.info("Loaded plugin: %s (v%s)", plugin_name, plugin.version)
                    return
            
            log.error("No Plugin class found in %s", name)
        except Exception:
            log.exception("Failed to load plugin %s", name)
    
    def unload_plugins(self) -> None:
        """Unload all plugins."""
        for name, plugin in self.plugins.items():
            try:
                plugin.on_unload()
                log.info("Unloaded plugin: %s", name)
            except Exception:
                log.exception("Error unloading plugin %s", name)
        self.plugins.clear()
    
    def get_plugin(self, name: str) -> Plugin | None:
        """Get a loaded plugin by name."""
        return self.plugins.get(name)
    
    def emit(self, event: str, data: Any) -> None:
        """Emit an event to all loaded plugins."""
        for name, plugin in self.plugins.items():
            try:
                method = getattr(plugin, f"on_{event}", None)
                if method:
                    method(data)
            except Exception:
                log.exception("Plugin %s error in event %s", name, event)
    
    def list_plugins(self) -> list[dict]:
        """List all loaded plugins with metadata."""
        return [
            {
                "name": p.name,
                "version": p.version,
                "description": p.description,
            }
            for p in self.plugins.values()
        ]