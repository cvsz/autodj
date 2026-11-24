__version__ = "0.3.13"

ABOUT_CREDIT = "camfrog:add:Seaza Dev @ZEAZDEV COMPANY LIMITED"
PROJECT_URL = "https://github.com/cvsz/autodj"


def about_text() -> str:
    """Text of the GUI About dialog (and anything else that shows program info)."""
    return f"AutoDJ {__version__}\n{ABOUT_CREDIT}\n{PROJECT_URL}"
