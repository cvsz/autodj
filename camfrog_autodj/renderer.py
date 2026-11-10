"""Message rendering for CamfrogAutoDJ.

Camfrog desktop client does NOT support rich text in outgoing messages.
All messages sent via UIA are plain text only.

This module provides:
1. A renderer for GUI preview (with font/style tags for tkinter Text widget)
2. A plain-text renderer for actual message sending (always returns plain text)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .config import MessageStyle


@dataclass
class RenderedMessage:
    """Result of rendering a message with a style."""

    plain_text: str
    # Rich text is always None for sending (Camfrog protocol limitation)
    # For GUI preview, use the tags in `preview_tags` with a tkinter Text widget
    rich_text: Optional[str] = None
    preview_tags: Optional[dict] = None  # For tkinter Text widget tag configuration


class MessageRenderer:
    """Render messages with optional font/style for preview.

    For sending: always returns plain text (Camfrog protocol limitation).
    For GUI preview: provides tag configuration for tkinter Text widget.
    """

    def __init__(self):
        pass

    def validate(self, text: str) -> Optional[str]:
        """Validate message text. Returns error message if invalid, None if valid."""
        if not text or not text.strip():
            return "Message cannot be empty"
        if len(text) > 10000:
            return "Message too long (max 10000 characters)"
        return None

    def render(self, style: MessageStyle, text: str) -> RenderedMessage:
        """Render message for sending (always plain text).

        Args:
            style: MessageStyle (used only for preview tags)
            text: Message text

        Returns:
            RenderedMessage with plain_text (for sending) and preview_tags (for GUI)
        """
        clean_text = text.strip()
        # For sending: always plain text - Camfrog does not support rich text
        # For preview: generate tkinter tag configuration
        preview_tags = self._make_preview_tags(style)
        return RenderedMessage(
            plain_text=clean_text,
            rich_text=None,  # Never rich text for sending
            preview_tags=preview_tags,
        )

    def render_preview(self, style: MessageStyle, text: str) -> tuple[str, dict]:
        """Render message for GUI preview.

        Returns:
            Tuple of (plain_text, tag_config_dict) for tkinter Text widget
        """
        rendered = self.render(style, text)
        return rendered.plain_text, rendered.preview_tags or {}

    def _make_preview_tags(self, style: MessageStyle) -> dict:
        """Create tkinter Text widget tag configuration for preview."""
        tags = {}
        tag_name = "preview_style"

        font_parts: list[str | int] = [style.font_family, style.font_size]
        if style.bold:
            font_parts.append("bold")
        if style.italic:
            font_parts.append("italic")
        if style.underline:
            font_parts.append("underline")

        tag_kwargs: dict[str, object] = {
            "font": tuple(font_parts),
            "foreground": style.font_color,
        }
        if style.underline:
            tag_kwargs["underline"] = True

        tags[tag_name] = tag_kwargs

        return tags


# Global renderer instance
_renderer: Optional[MessageRenderer] = None


def get_renderer() -> MessageRenderer:
    """Get global renderer instance (singleton)."""
    global _renderer
    if _renderer is None:
        _renderer = MessageRenderer()
    return _renderer
