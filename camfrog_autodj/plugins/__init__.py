"""Plugin system for CamfrogAutoDJ.

Provides a modular plugin architecture for extending AutoDJ functionality.
"""

from __future__ import annotations

from .base import Plugin, PluginInterface
from .manager import PluginManager

__all__ = [
    "Plugin",
    "PluginInterface",
    "PluginManager",
]