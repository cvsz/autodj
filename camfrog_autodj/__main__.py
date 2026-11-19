import argparse
import logging
import logging.handlers
import os
import shutil
import sys
from pathlib import Path

from . import __version__
from .adapters import NullAdapter, build_adapter
from .config import Config, ConfigError
from .engine import Engine
from .logging_json import add_json_file_handler, configure_json_logging
from .migrate import migrate_config
from .textutil import clean_text

log = logging.getLogger(__name__)


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="camfrog-autodj")
    ap.add_argument("-c", "--config", default="config.toml")
    ap.add_argument("--version", action="version", version=f"AutoDJ {__version__}")
    ap.add_argument("--console", action="store_true", help="chat via stdin/stdout (no Camfrog)")
    ap.add_argument("--gui", action="store_true", help="open the desktop window")
    ap.add_argument("--lang", choices=["en", "th"], help="override config lang")
    ap.add_argument(
        "--check",
        action="store_true",
        help="check the setup (config, mpv, yt-dlp, folders, Camfrog window) and exit",
    )
    ap.add_argument(
        "--discover",
        action="store_true",
        help="find the room window and chat controls, save them to config.toml, then exit",
    )
    ap.add_argument(
        "--windows",
        action="store_true",
        help="list every visible window (exe, pid, class, title) and exit: shows what Camfrog looks like",
    )
    ap.add_argument(
        "--dump",
        metavar="TITLE_RE",
        help="print the control tree of the first window matching TITLE_RE and exit (use > tree.txt)",
    )
    ap.add_argument(
        "--say",
        metavar="TEXT",
        help="send TEXT into the room once and exit (tests chat sending)",
    )
    ap.add_argument("--no-discover", action="store_true", help="skip startup auto-discovery")
    ap.add_argument(
        "--log-file",
        metavar="PATH",
        help="also write the log to PATH (rotating); or set log_file in config",
    )
    ap.add_argument(
        "--log-json",
        action="store_true",
        help="output logs in JSON format (structured logging)",
    )
    ap.add_argument("-v", "--verbose", action="store_true")
    return ap


def _add_log_file(path: str, level: int):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    h = logging.handlers.RotatingFileHandler(
        path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    h.setLevel(level)
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.getLogger().addHandler(h)


def main():
    a = _parser().parse_args()
    level = logging.DEBUG if a.verbose else logging.INFO

    # Always install a console handler: no flag may silence startup logging.
    # _configure_logging() switches the formatter to JSON once config is loaded.
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")

    try:
        _run(a, level)
    except ConfigError as ex:
        print(f"\nCannot start: {ex}\n", file=sys.stderr)
        sys.exit(2)
    except RuntimeError as ex:  # e.g. the Camfrog room window is not open
        log.error("%s", ex)
        sys.exit(1)


def _configure_logging(a, cfg, level):
    """Configure logging (JSON or text) based on CLI flags and config."""
    if a.log_json or getattr(cfg, "log_json", False):
        # Remove any existing handlers
        root_logger = logging.getLogger()
        for h in root_logger.handlers[:]:
            root_logger.removeHandler(h)
        # Add JSON console handler
        configure_json_logging(cfg, level=level)
        # Always write JSON logs to <install>/logs/ (APPDATA fallback).
        from .paths import resolve_log_path

        log_path = resolve_log_path(a.log_file or cfg.log_file)
        try:
            add_json_file_handler(cfg, str(log_path), level=level)
        except (OSError, PermissionError):
            log.warning(
                "cannot open log file %s; continuing without file logging",
                log_path,
            )
    else:
        # Standard text logging (handlers already set up by basicConfig)
        _setup_log_file(a, cfg, level)


def _apply_startup_update(cfg) -> bool:
    """Download and apply a newer AutoDJ.exe before the bot starts.

    Returns True when the swap script was launched and startup must stop.
    """
    if not (cfg.auto_update_enabled and cfg.auto_update_apply_on_start):
        return False
    from .updater import Updater

    updater = Updater(cfg)
    if not (updater.check_for_update() and updater.apply_update()):
        return False
    log.info("auto-update: staged update, replacing the installed AutoDJ.exe")
    return updater.launch_update_script()


def _load_startup_config(a, level):
    """Resolve, migrate, load and configure logging for the startup config."""
    _resolve_frozen_config_path(a)
    if os.path.exists(a.config):
        log.info("config: %s", os.path.abspath(a.config))
    else:
        log.warning(
            "config file %s not found: running with built-in defaults (copy config.example.toml to config.toml)",
            os.path.abspath(a.config),
        )
    _migrate_config(a.config)
    cfg = Config.load(a.config)
    _configure_logging(a, cfg, level)
    cfg = _relocate_config(a, cfg)
    if a.lang:
        cfg.lang = a.lang
    if a.console:
        cfg.chat_reader = cfg.chat_sender = "console"
    return cfg


def _run(a, level):
    if _handle_windows(a):
        return
    if _handle_dump(a):
        return
    cfg = _load_startup_config(a, level)
    if _run_check(a, cfg):
        return
    _auto_launch(cfg)
    if _auto_discover(a, cfg):
        return
    if _run_say(a, cfg):
        return
    if _apply_startup_update(cfg):
        return  # the batch file relaunches the freshly installed exe
    adapter = _build_adapter(a, cfg)
    eng = Engine(cfg, adapter, cfg_path=a.config)
    if a.gui:
        _run_gui(eng)
    else:
        eng.run()


def _run_gui(eng) -> None:
    """Start the engine and open the Tk desktop window.

    ``camfrog_autodj.gui`` is imported lazily here (only under ``--gui``) so
    headless / console runs never pull in tkinter.  The import is wrapped so a
    shadowing/stale installed copy (older builds lack gui.py) yields an
    actionable error instead of a bare ModuleNotFoundError.
    """
    try:
        from .gui import App
    except ImportError:
        pkg = sys.modules.get("camfrog_autodj")
        pkg_file = getattr(pkg, "__file__", "<unknown>")
        print(
            "\nCannot start GUI: 'camfrog_autodj.gui' could not be imported.\n"
            f"  The 'camfrog_autodj' package was loaded from: {pkg_file}\n"
            "  This usually means a stale pip-installed copy of camfrog-autodj\n"
            "  (older builds do not ship gui.py) is shadowing this repo's source.\n"
            "  Fix:\n"
            "    pip uninstall camfrog-autodj -y\n"
            "    python run_autodj.py --gui\n"
            "  Or install this repo editable:\n"
            "    pip install -e .\n",
            file=sys.stderr,
        )
        raise

    eng.start()
    App(eng).mainloop()


def _handle_windows(a) -> bool:
    if not a.windows:
        return False
    from .windows import list_all

    for c in list_all():
        print(f"exe={c.exe!r} pid={c.pid} class={c.cls!r} title={c.title!r}")
    return True


def _handle_dump(a) -> bool:
    if not a.dump:
        return False
    from pywinauto import Desktop  # type: ignore[import-untyped]  # pywinauto ships no py.typed stubs

    from .windows import candidates

    cs = [c for c in candidates(a.dump, visible_only=False) if c.pid != os.getpid()]
    if not cs:
        print("no window matches", a.dump)
        return True
    Desktop(backend="uia").window(handle=cs[0].handle).print_control_identifiers()
    return True


def _resolve_frozen_config_path(a) -> None:
    # exe: also look next to AutoDJ.exe
    if not os.path.exists(a.config) and getattr(sys, "frozen", False):
        alt = os.path.join(os.path.dirname(sys.executable), os.path.basename(a.config))
        if os.path.exists(alt):
            a.config = alt


def _migrate_config(path: str) -> None:
    # Migrate placeholder/invalid values before loading config.
    if not os.path.exists(path):
        return
    try:
        changes = migrate_config(path)
        for change in changes:
            log.info("config migration: %s", change)
    except Exception:  # migration must never prevent startup
        log.exception("config migration failed; continuing with existing config")


def _setup_log_file(a, cfg, level) -> None:
    # Default: <install>/logs/autodj.log so actions are inspectable next to the
    # installed program. Falls back to APPDATA when the install dir is read-only.
    from .paths import resolve_log_path

    log_path = resolve_log_path(a.log_file or cfg.log_file)
    try:
        _add_log_file(str(log_path), level)
    except (OSError, PermissionError):
        log.warning(
            "cannot open log file %s; continuing without file logging",
            log_path,
        )


def _relocate_config(a, cfg):
    # If config file is not writable (e.g. installed to Program Files), relocate to APPDATA
    # so settings changes and auto-discover can be saved.
    p = Path(a.config)
    if p.exists() and os.access(p, os.W_OK):
        return cfg
    app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
    app_cfg_dir = Path(app_data) / "Camfrog AutoDJ"
    app_cfg_dir.mkdir(parents=True, exist_ok=True)
    app_cfg_path = app_cfg_dir / "config.toml"
    if p.exists() and not app_cfg_path.exists():
        shutil.copyfile(p, app_cfg_path)
        log.info(
            "config.toml not writable at %s; using %s instead",
            p,
            app_cfg_path,
        )
    p = app_cfg_path
    a.config = str(p)
    # Migrate the relocated config before loading
    _migrate_config(str(p))
    return Config.load(str(p))


def _run_check(a, cfg) -> bool:
    if not a.check:
        return False
    from . import doctor

    res = doctor.run_checks(cfg)
    print(doctor.format_report(res))
    sys.exit(1 if doctor.has_failures(res) else 0)


def _auto_launch(cfg) -> None:
    if not (cfg.auto_launch and "uia" in (cfg.chat_reader, cfg.chat_sender)):
        return
    from .launcher import ensure_room

    try:
        ensure_room(cfg)
    except Exception as ex:  # noqa: BLE001 -- defensive; auto-launch must not crash the bot
        log.warning("auto-launch failed; continuing without Camfrog: %s", ex)


def _auto_discover(a, cfg) -> bool:
    # Auto-discovery must never prevent the GUI from opening: log the failure
    # and continue with the existing config instead of crashing at startup.
    uses_uia = "uia" in (cfg.chat_reader, cfg.chat_sender)
    if not (uses_uia and (a.discover or (cfg.auto_discover and not a.no_discover))):
        return False
    from . import discover

    try:
        ups = discover.apply(cfg, a.config)
    except Exception:  # pragma: no cover - defensive; discovery is best-effort
        logging.getLogger(__name__).exception("auto-discover failed; continuing without it")
        ups = None
    if a.discover:
        print(ups or "nothing found: open the room window and try again")
        return True
    return False


def _run_say(a, cfg) -> bool:
    if not a.say:
        return False
    ad = build_adapter(cfg)
    ad.send(clean_text(a.say))
    print("sent:", a.say)
    return True


def _build_adapter(a, cfg):
    try:
        return build_adapter(cfg)
    except Exception as ex:  # Camfrog not open / pywinauto unavailable, ...
        if a.gui:
            # The window must still open so the user can run --check / --discover
            # from inside it; chat degrades to silent until Camfrog is reachable.
            log.error(
                "cannot attach to Camfrog chat (%s); opening the GUI without chat",
                ex,
            )
            return NullAdapter()
        raise


if __name__ == "__main__":
    main()
