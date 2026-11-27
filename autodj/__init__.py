__version__ = "0.4.1"

ABOUT_CREDIT = "camfrog:add:Seaza Dev @ZEAZDEV COMPANY LIMITED"
PROJECT_URL = "https://github.com/cvsz/autodj"

__all__ = ["__version__", "ABOUT_CREDIT", "PROJECT_URL", "about_text"]


def about_text() -> str:
    """Text of the GUI About dialog (and anything else that shows program info)."""
    return f"zAutoDJ {__version__}\n{ABOUT_CREDIT}\n{PROJECT_URL}"
