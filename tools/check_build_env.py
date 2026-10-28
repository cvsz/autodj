"""Pre-flight for build.ps1: is everything AutoDJ.exe must contain installed in THIS Python?
PyInstaller can only bundle what is importable at build time; a missing package does not stop the build, it just
produces an exe that fails later (e.g. "No module named 'yt_dlp'"). Exit code 1 + a fix-it line if anything is missing."""
import importlib.util
import sys

REQUIRED = {  # module: what breaks without it
    "yt_dlp": "YouTube links and song-name requests",
    "mutagen": "titles/durations of local files",
    "pyttsx3": "text-to-speech",
    "pywinauto": "reading/sending Camfrog chat (UI Automation)",
    "pyperclip": "sending chat in foreground mode",
    "comtypes": "Windows UI Automation",
    "PyInstaller": "building the exe",
}


def missing(find=importlib.util.find_spec) -> dict[str, str]:
    out = {}
    for mod, why in REQUIRED.items():
        try:
            if find(mod) is None:
                out[mod] = why
        except (ImportError, ValueError):
            out[mod] = why
    return out


def main() -> int:
    bad = missing()
    print(f"python: {sys.executable}")
    if not bad:
        print("build environment OK: " + ", ".join(REQUIRED))
        return 0
    for mod, why in bad.items():
        print(f"  MISSING {mod:<10} -> without it: {why}")
    print("Fix:  python -m pip install -e . pyinstaller      (then run build.ps1 again)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
