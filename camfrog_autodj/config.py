class MessageStyle:
    """Style for message display (GUI preview only; Camfrog sends plain text)."""

    def __init__(self, font_family="Consolas", font_size=14, font_color="#000000",
                 bold=False, italic=False, underline=False):
        self.font_family = font_family
        self.font_size = font_size
        self.font_color = font_color
        self.bold = bold
        self.italic = italic
        self.underline = underline

    @classmethod
    def from_toml_dict(cls, data):
        """Create from TOML dict with defaults."""
        return cls(
            font_family=data.get("font_family", "Consolas"),
            font_size=int(data.get("font_size", 14)),
            font_color=data.get("font_color", "#000000"),
            bold=bool(data.get("bold", False)),
            italic=bool(data.get("italic", False)),
            underline=bool(data.get("underline", False)),
        )
